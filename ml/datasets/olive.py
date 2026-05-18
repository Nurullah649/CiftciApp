"""Olive (Zeytin) Leaf Disease dataset downloader & integrator.

Kaynak: sinanuguz/CNN_olive_dataset (GitHub) — Denizli, Türkiye'den toplanmış
   ~3400 zeytin yaprağı görseli, 3 sınıf:
       - Healthy (sağlıklı)
       - Aculus olearius (Zeytin akarı — Aculus olearius)
       - Olive peacock spot (Tavuskuşu gözü hastalığı — Spilocaea oleagina)
   Çalışma: Uguz, S., Uysal, N. (2020). "Classification of olive leaf diseases
            using deep convolutional neural networks." Neural Computing & Apps.

Bu modül:
    1. GitHub'tan 5 RAR dosyasını indirir (Train1-4 + test)
    2. ml/data/external/olive/ altına extract eder (rarfile/patool/7z)
    3. Sınıfları birleşik taksonomi ile raw/'a entegre eder

NOT: RAR extraction için sisteminde 7-Zip veya WinRAR olmalı.
     Yoksa: winget install 7zip.7zip
            VEYA https://www.7-zip.org/ den indir.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent))

from ml.datasets import (
    DEFAULT_EXTERNAL_DIR,
    DEFAULT_RAW_DIR,
    download_url,
    extract_rar,
    list_images_recursive,
    merge_into_raw,
    print_step,
    safe_dirname,
)

OLIVE_REPO_BASE = "https://raw.githubusercontent.com/sinanuguz/CNN_olive_dataset/master"
OLIVE_FILES = ["Train1.rar", "Train2.rar", "train3.rar", "train4.rar", "test.rar"]
EXTERNAL_NAME = "olive"


# sinanuguz dataset yapısı (RAR'lar açılınca):
#   Train1/Healthy/*.jpg           → Healthy (830)
#   Train2/aculus_olearius/*.jpg   → Aculus (690)
#   train3/train3/*.jpg            → Aculus (423, dosya adı paterni: A-13.JPG, A119.jpg)
#   train4/train4/*.jpg            → Peacock (777, dosya adı paterni: IMG_20190806_xxxx.jpg)
#   test/test/<class>/*.jpg        → 200 aculus + 220 healthy + 260 peacock
#
# train3 ve train4 klasörleri etiketsiz, dosya adı paterniyle ayırıyoruz.
CLASS_KEYWORDS = {
    "Olive___healthy": ["healthy", "saglikli", "sağlıklı", "fresh"],
    "Olive___Aculus_olearius": ["aculus", "akar", "mite"],
    "Olive___Peacock_spot": ["peacock", "tavuskus", "spilocaea", "spot"],
}


def classify_folder_name(folder_name: str) -> str | None:
    """Folder ismine bakarak hangi birleşik sınıfa düştüğünü bul."""
    lname = folder_name.lower().replace("_", " ").replace("-", " ")
    for unified, keywords in CLASS_KEYWORDS.items():
        for kw in keywords:
            if kw in lname:
                return unified
    return None


def classify_by_filename(filename: str, parent_path: str) -> str | None:
    """train3/train4 gibi etiketsiz klasörler için sınıf çıkar.

    Heuristik (sinanuguz dataset için):
        - train3/ tüm dosyalar → Aculus
          (Train2 zaten aculus, train3 ek aculus partition'ı — dosya adları çoğunlukla A-prefix)
        - train4/ tüm dosyalar → Peacock_spot
          (test/olive_peacock_spot ile IMG_2019 naming paylaşıyor)

    Toplam: 830+220 healthy, 690+423+200 aculus, 777+260 peacock = 3400 (Uguz 2020 ile uyumlu).
    """
    parent = parent_path.lower()
    if "train3" in parent:
        return "Olive___Aculus_olearius"
    elif "train4" in parent:
        return "Olive___Peacock_spot"
    return None


def download_olive_rars(out_dir: Path, force: bool = False) -> list[Path]:
    """5 RAR dosyasını GitHub'tan indir."""
    print_step("Olive RAR dosyaları indirme")
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for fname in OLIVE_FILES:
        url = f"{OLIVE_REPO_BASE}/{fname}"
        dst = out_dir / fname
        if dst.exists() and not force:
            print(f"  [SKIP] {fname} mevcut ({dst.stat().st_size / (1024*1024):.1f} MB)")
        else:
            try:
                download_url(url, dst)
            except Exception as e:
                print(f"  [HATA] {fname} indirilemedi: {e}")
                continue
        paths.append(dst)
    return paths


def extract_olive_rars(rar_paths: list[Path], extract_dir: Path, force: bool = False) -> int:
    """Tüm RAR'ları extract et."""
    print_step("Olive RAR extract")
    extract_dir.mkdir(parents=True, exist_ok=True)
    flag = extract_dir / ".extracted"
    if flag.exists() and not force:
        files = list_images_recursive(extract_dir)
        if files:
            print(f"  [SKIP] Önceden extract edilmiş ({len(files)} görsel)")
            return len(files)

    total = 0
    for rar in rar_paths:
        sub = extract_dir / rar.stem
        sub.mkdir(parents=True, exist_ok=True)
        print(f"  [EXT] {rar.name} -> {sub.name}/")
        n = extract_rar(rar, sub)
        total += n
        if n == 0:
            print(f"        (Extract başarısız — RAR aracı eksik mi?)")
    if total > 0:
        flag.write_text("ok", encoding="utf-8")
    print(f"  [DONE] Toplam {total} dosya extract edildi.")
    return total


def integrate_olive(extracted_dir: Path, raw_dir: Path = DEFAULT_RAW_DIR, validate: bool = True) -> dict:
    print_step("Olive -> raw/ entegrasyonu")

    if not extracted_dir.exists():
        print(f"  [HATA] {extracted_dir} yok.")
        return {}

    by_class: dict[str, list[Path]] = {"Olive___healthy": [], "Olive___Aculus_olearius": [], "Olive___Peacock_spot": []}
    unmapped: dict[str, list[Path]] = {}

    for sub in extracted_dir.rglob("*"):
        if not sub.is_dir():
            continue
        imgs = [p for p in sub.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
        if not imgs:
            continue

        # 1) Klasör adından sınıf çıkar
        unified = classify_folder_name(sub.name)
        if unified is None and sub.parent != extracted_dir:
            unified = classify_folder_name(sub.parent.name)

        if unified is not None:
            by_class[unified].extend(imgs)
            continue

        # 2) Etiketsiz klasör (train3/train4) — dosya adı paterni
        grouped_by_pattern: dict[str, list[Path]] = {}
        for img in imgs:
            pattern_cls = classify_by_filename(img.name, str(sub))
            if pattern_cls:
                grouped_by_pattern.setdefault(pattern_cls, []).append(img)

        if grouped_by_pattern:
            for cls, files in grouped_by_pattern.items():
                by_class[cls].extend(files)
                print(f"    [pattern] {sub.name}/ -> {cls} ({len(files)} dosya, dosya adı paterniyle)")
        else:
            unmapped.setdefault(sub.name, []).extend(imgs)

    print(f"  [INFO] Bulunan sınıflar:")
    stats = {"written": 0, "invalid": 0}
    for uni, imgs in by_class.items():
        if not imgs:
            print(f"    {uni:<40s}: 0 görsel  [UYARI: bu sınıf eksik!]")
            continue
        written, invalid = merge_into_raw(
            source="olive",
            source_class=uni,
            unified_class=uni,
            images=imgs,
            raw_dir=raw_dir,
            validate=validate,
        )
        stats["written"] += written
        stats["invalid"] += invalid
        print(f"    {uni:<40s}: {len(imgs):>4} görsel  [w={written} inv={invalid}]")

    if unmapped:
        print()
        print(f"  [UYARI] {len(unmapped)} klasör adı eşlenemedi (atlandı):")
        for k, v in list(unmapped.items())[:10]:
            print(f"    - {k} ({len(v)} görsel)")

    print()
    print(f"  Toplam yazılan: {stats['written']}")
    print(f"  Bozuk         : {stats['invalid']}")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-dir", type=Path, default=DEFAULT_EXTERNAL_DIR / EXTERNAL_NAME)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--integrate-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args()

    rar_dir = args.external_dir / "rars"
    extracted_dir = args.external_dir / "extracted"

    if not args.integrate_only:
        rars = download_olive_rars(rar_dir, force=args.force)
        if not rars:
            print("[HATA] Hiç RAR indirilemedi.")
            return 1
        n_extracted = extract_olive_rars(rars, extracted_dir, force=args.force)
        if n_extracted == 0:
            print()
            print("[KRITIK] RAR extraction başarısız.")
            print("         Sisteminde 7-Zip veya WinRAR kurulu olmalı.")
            print("         Çözüm 1: winget install 7zip.7zip   (PowerShell admin)")
            print("         Çözüm 2: https://www.7-zip.org/ den indir, PATH'e ekle")
            print("         Kurduktan sonra: python -m ml.datasets.olive --integrate-only")
            return 1

    if not args.download_only:
        integrate_olive(extracted_dir, args.raw_dir, validate=not args.no_validate)

    print()
    print("[DONE] Olive entegrasyonu tamamlandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
