"""
PlantVillage dataset indirme scripti — HuggingFace `mohanty/PlantVillage` kaynağından.

Bu script, 38 sınıflı (14 bitki + 26 hastalık + sağlıklı varyantlar) PlantVillage
dataset'ini indirir ve `ml/data/raw/<sinif>/<leaf_id>__<idx>.jpg` formatında diske
yazar. `leaf_id` dosya adında saklandığı için `prepare_dataset.py --leaf-aware`
ile aynı yaprağın görsellerinin train/val/test arasında dağılmamasını sağlayabilir.

Tasarım notu (Neden direkt HF Hub'dan zip indiriyoruz?):
    `datasets>=4.0`, özel loading script'i olan dataset'ler için `trust_remote_code`
    desteğini kaldırdı. `mohanty/PlantVillage` özel `plant_village.py` script'i
    kullandığı için `load_dataset(..., trust_remote_code=True)` artık çalışmıyor.
    Çözüm: `data.zip` + split listeleri + leaf-map.json'u doğrudan HF Hub'dan
    indirip, kendi extract logic'imizi uyguluyoruz. Plant_village.py'deki
    leaf_id çıkarım mantığını birebir taklit ediyoruz.

Kullanım:
    # Tüm 38 sınıfı indir (~2.2 GB indir, ~1.5 GB extracted)
    python ml/download_dataset.py

    # Sadece eksik sınıfları indir (raw/'da olmayanlar)
    python ml/download_dataset.py --only-missing

    # Belirli sınıfları indir
    python ml/download_dataset.py --classes Tomato___Late_blight Potato___Early_blight

    # Farklı varyant
    python ml/download_dataset.py --variant segmented

Gereksinim:
    pip install huggingface_hub pillow tqdm
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ML_DIR = Path(__file__).resolve().parent
DEFAULT_RAW_DIR = ML_DIR / "data" / "raw"
DEFAULT_LABELS_PATH = ML_DIR / "class_labels.json"
DEFAULT_REPO = "mohanty/PlantVillage"
ALL_VARIANTS = ("color", "grayscale", "segmented")


def load_expected_classes(labels_path: Path) -> Set[str]:
    if not labels_path.exists():
        return set()
    data = json.loads(labels_path.read_text(encoding="utf-8"))
    return set(data.get("classes", {}).keys())


def existing_nonempty_classes(raw_dir: Path) -> Set[str]:
    if not raw_dir.exists():
        return set()
    return {
        p.name for p in raw_dir.iterdir()
        if p.is_dir() and any(
            f.suffix.lower() in {".jpg", ".jpeg", ".png"}
            for f in p.iterdir() if f.is_file()
        )
    }


def hf_download(repo: str, filename: str, hf_token: Optional[str] = None) -> Path:
    """HF Hub'dan tek bir dosyayı indir, lokal cache yolunu döndür."""
    from huggingface_hub import hf_hub_download
    print(f"[INFO] HF Hub: {filename} indiriliyor...")
    path = hf_hub_download(
        repo_id=repo,
        repo_type="dataset",
        filename=filename,
        token=hf_token,
    )
    return Path(path)


def compute_leaf_id(filename: str, class_name: str, leaf_map: Dict[str, List[str]]) -> str:
    """plant_village.py'deki leaf_id çıkarım logic'ini birebir uygula.

    Algoritma:
        1) Dosya adından '_final_masked' temizle
        2) '___' içeriyorsa son parçayı al
        3) 'copy' kelimesine kadar olan kısmı al
        4) Uzantıyı kaldır, lowercase'e çevir, leaf-map'te ara
        5) Birden fazla aday varsa class_name içerene bak
        6) Yoksa 'fallback_<id>' formatında üret
    """
    image_identifier = filename.replace("_final_masked", "")
    if "___" in image_identifier:
        image_identifier = image_identifier.split("___")[-1]
    image_identifier = image_identifier.split("copy")[0]
    for ext in (".jpg", ".JPG", ".png", ".PNG", ".jpeg", ".JPEG"):
        image_identifier = image_identifier.replace(ext, "")
    image_identifier = image_identifier.strip()

    lookup_key = image_identifier.lower().strip()

    if lookup_key in leaf_map:
        suggestions = leaf_map[lookup_key]
        if isinstance(suggestions, list):
            if len(suggestions) == 1:
                return str(suggestions[0])
            for s in suggestions:
                if class_name in str(s):
                    return str(s)
            return f"fallback_{image_identifier}"
        return str(suggestions)
    return f"fallback_{image_identifier}"


def safe_leaf_filename(leaf_id: str, idx: int, suffix: str) -> str:
    """leaf_id'yi dosya sistemine uygun hale getir."""
    token = "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(leaf_id))
    token = token.strip("_") or "noleaf"
    if len(token) > 80:
        token = token[:80]
    return f"{token}__{idx:06d}{suffix}"


def parse_split_file(path: Path) -> List[str]:
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def class_from_relpath(rel: str) -> Optional[str]:
    """'raw/color/Apple___Apple_scab/foo.JPG' -> 'Apple___Apple_scab'"""
    parts = rel.replace("\\", "/").split("/")
    if len(parts) >= 4 and parts[0] == "raw":
        return parts[2]
    return None


def filename_from_relpath(rel: str) -> str:
    return rel.replace("\\", "/").rsplit("/", 1)[-1]


def download_and_extract(
    raw_dir: Path,
    repo: str,
    variant: str,
    target_classes: Optional[Set[str]],
    skip_existing: bool,
    max_per_class: Optional[int],
    hf_token: Optional[str],
    save_hf_split: bool,
) -> None:
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    leaf_map_path = hf_download(repo, "leaf_grouping/leaf-map.json", hf_token)
    train_list_path = hf_download(repo, f"splits/{variant}_train.txt", hf_token)
    test_list_path = hf_download(repo, f"splits/{variant}_test.txt", hf_token)

    leaf_map: Dict[str, List[str]] = json.loads(leaf_map_path.read_text(encoding="utf-8"))
    train_paths = parse_split_file(train_list_path)
    test_paths = parse_split_file(test_list_path)

    train_set = set(train_paths)
    print(f"[INFO] leaf-map: {len(leaf_map)} kayit  |  train: {len(train_paths)}  |  test: {len(test_paths)}")

    target_relpaths: Dict[str, List[str]] = {}
    for rel in train_paths + test_paths:
        cls = class_from_relpath(rel)
        if cls is None:
            continue
        if target_classes is not None and cls not in target_classes:
            continue
        target_relpaths.setdefault(cls, []).append(rel)

    if not target_relpaths:
        print("[WARN] Hedef sınıflar için kayıt bulunamadı.")
        return

    total_target = sum(len(v) for v in target_relpaths.values())
    print(f"[INFO] {len(target_relpaths)} sınıf, {total_target} hedef görsel.")

    zip_path = hf_download(repo, "data.zip", hf_token)
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[INFO] data.zip indirildi: {zip_path}  ({zip_size_mb:,.1f} MB)")

    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = lambda it, **kw: it  # type: ignore

    written = 0
    skipped = 0
    errors = 0
    per_class: Dict[str, int] = {}
    hf_split_map: Dict[str, Dict[str, str]] = {}

    print(f"[INFO] Zip içeriği işleniyor...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zip_names = set(zf.namelist())

        for cls, rels in sorted(target_relpaths.items()):
            (raw_dir / cls).mkdir(parents=True, exist_ok=True)
            per_class[cls] = 0
            pbar = tqdm(rels, desc=cls[:40], leave=False, unit="img")
            for rel in pbar:
                if max_per_class is not None and per_class[cls] >= max_per_class:
                    continue

                if rel not in zip_names:
                    if rel.replace("/", "\\") in zip_names:
                        rel_in_zip = rel.replace("/", "\\")
                    else:
                        errors += 1
                        continue
                else:
                    rel_in_zip = rel

                orig_name = filename_from_relpath(rel)
                suffix = Path(orig_name).suffix or ".jpg"
                leaf_id = compute_leaf_id(orig_name, cls, leaf_map)
                dst_name = safe_leaf_filename(leaf_id, per_class[cls], suffix)
                dst = raw_dir / cls / dst_name

                if skip_existing and dst.exists():
                    skipped += 1
                    per_class[cls] += 1
                    hf_split_map.setdefault(cls, {})[dst_name] = "train" if rel in train_set else "test"
                    continue

                try:
                    with zf.open(rel_in_zip) as src, open(dst, "wb") as out:
                        out.write(src.read())
                    written += 1
                    per_class[cls] += 1
                    hf_split_map.setdefault(cls, {})[dst_name] = "train" if rel in train_set else "test"
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"\n  [WARN] {rel}: {e}")

    if save_hf_split and hf_split_map:
        split_path = raw_dir / "hf_official_split.json"
        split_path.write_text(
            json.dumps({
                "_meta": {
                    "source": repo,
                    "variant": variant,
                    "description": "Mohanty et al. 2016 resmi train/test bölmesi (leaf-aware).",
                },
                "split": hf_split_map,
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[INFO] HF resmi split kaydedildi: {split_path}")

    print()
    print("=" * 60)
    print("INDIRME TAMAMLANDI")
    print(f"  Yazılan görsel : {written}")
    print(f"  Atlanan (mevcut): {skipped}")
    print(f"  Hata           : {errors}")
    print(f"  Sınıf sayısı   : {len(per_class)}")
    print()
    print("Sınıf başına görsel sayısı:")
    for cls in sorted(per_class):
        print(f"  {cls:<55s}  {per_class[cls]:>5d}")
    print("=" * 60)
    print(f"  Çıktı: {raw_dir}")
    print()
    print("Sonraki adım:")
    print("  python ml/verify_dataset.py ml/data/raw")
    print("  python ml/prepare_dataset.py --leaf-aware --clean")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PlantVillage dataset'ini HuggingFace'ten indir (38 sınıf, 54k görsel)."
    )
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR,
                        help=f"Çıktı klasörü (varsayılan: {DEFAULT_RAW_DIR})")
    parser.add_argument("--repo", default=DEFAULT_REPO,
                        help=f"HF repo (varsayılan: {DEFAULT_REPO})")
    parser.add_argument("--variant", choices=ALL_VARIANTS, default="color",
                        help="Görsel varyantı (color/grayscale/segmented)")
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS_PATH)
    parser.add_argument("--classes", nargs="+",
                        help="Sadece bu sınıfları indir (boşlukla ayrılmış liste)")
    parser.add_argument("--only-missing", action="store_true",
                        help="raw/'da zaten olan sınıfları atla, sadece eksikleri indir")
    parser.add_argument("--no-skip-existing", action="store_true",
                        help="Aynı dosya adı varsa üzerine yaz (varsayılan: atla)")
    parser.add_argument("--max-per-class", type=int, default=None,
                        help="Debug: sınıf başına maks görsel sayısı")
    parser.add_argument("--no-save-split", action="store_true",
                        help="hf_official_split.json yazma")
    parser.add_argument("--hf-token", default=None,
                        help="HF token (gerekli değil — public dataset)")
    args = parser.parse_args()

    try:
        import huggingface_hub  # noqa: F401
    except ImportError:
        print(
            "[ERROR] `huggingface_hub` kütüphanesi bulunamadı.\n"
            "        Yükle:  pip install huggingface_hub pillow tqdm\n"
            "        Veya:   pip install -r ml/requirements-ml.txt"
        )
        return 1

    expected = load_expected_classes(args.labels)

    target: Optional[Set[str]] = None
    if args.classes:
        target = set(args.classes)
        if expected:
            unknown = target - expected
            if unknown:
                print("[WARN] class_labels.json'da olmayan sınıflar:")
                for u in sorted(unknown):
                    print(f"   - {u}")
    elif args.only_missing:
        if not expected:
            print("[ERROR] --only-missing için class_labels.json gerekli.")
            return 1
        existing = existing_nonempty_classes(args.raw_dir)
        target = expected - existing
        if not target:
            print("[INFO] Tüm beklenen sınıflar raw/'da mevcut, indirilecek bir şey yok.")
            return 0
        print(f"[INFO] Eksik {len(target)} sınıf indirilecek:")
        for cls in sorted(target):
            print(f"   - {cls}")

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    download_and_extract(
        raw_dir=args.raw_dir,
        repo=args.repo,
        variant=args.variant,
        target_classes=target,
        skip_existing=not args.no_skip_existing,
        max_per_class=args.max_per_class,
        hf_token=args.hf_token,
        save_hf_split=not args.no_save_split,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
