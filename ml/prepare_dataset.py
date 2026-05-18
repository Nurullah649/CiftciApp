"""
PlantVillage dataset hazırlık scripti.

Kullanım:
    1) Dataset'i Kaggle'dan indir:
       https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset
    2) `plantvillage-dataset.zip` dosyasını aç. İçindeki `color/` klasörünü
       bu projedeki `ml/data/raw/` altına kopyala.
       Yapı şöyle olmalı:
           ml/data/raw/
               ├── Apple___Apple_scab/
               ├── Apple___Black_rot/
               ├── ... (38 klasör)
               └── Tomato___healthy/
    3) Bu scripti çalıştır:
           python ml/prepare_dataset.py

Çıktı:
    ml/data/splits/
        ├── train/  (%70)
        ├── val/    (%15)
        └── test/   (%15)

Notlar:
    - Stratified split: her sınıfın oranı korunur.
    - shutil.copy2 yerine os.symlink öncelikli (disk tasarrufu).
      Windows'ta sembolik link izniniz yoksa otomatik kopyalamaya düşer.
    - Seed sabit (42) -> tekrar üretilebilir bölme.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

ML_DIR = Path(__file__).resolve().parent
DEFAULT_RAW_DIR = ML_DIR / "data" / "raw"
DEFAULT_SPLIT_DIR = ML_DIR / "data" / "splits"
DEFAULT_LABELS_PATH = ML_DIR / "class_labels.json"
SEED = 42
VALID_EXT = {".jpg", ".jpeg", ".png"}


def collect_files(class_dir: Path) -> List[Path]:
    files = [p for p in class_dir.iterdir() if p.is_file() and p.suffix.lower() in VALID_EXT]
    files.sort()
    return files


def split_indices(n: int, ratios: Tuple[float, float, float]) -> Tuple[List[int], List[int], List[int]]:
    train_r, val_r, _ = ratios
    indices = list(range(n))
    random.Random(SEED).shuffle(indices)
    train_end = int(n * train_r)
    val_end = train_end + int(n * val_r)
    return indices[:train_end], indices[train_end:val_end], indices[val_end:]


def _leaf_id_from_name(name: str) -> str:
    """download_dataset.py'nin yazdığı '<leaf_id>__<idx>.<ext>' formatından leaf_id'yi çıkar.

    Bu kalıba uymayan dosyalar için (Kaggle'dan elle kopyalanmış gibi) dosya adının
    kendisi leaf_id olarak kullanılır → her dosya tek yaprak sayılır (klasik random split davranışı).

    NOT: rsplit kullanıyoruz çünkü leaf_id'nin kendisi '___' içerebilir
    (ör. 'Tomato___healthy___245_0__000001.jpg' → leaf_id='Tomato___healthy___245_0', idx='000001')."""
    base = name.rsplit(".", 1)[0]
    if "__" in base:
        return base.rsplit("__", 1)[0]
    return base


def split_indices_by_leaf(
    files: List[Path], ratios: Tuple[float, float, float],
) -> Tuple[List[int], List[int], List[int]]:
    """Aynı leaf_id'ye sahip görseller TEK bir split'e gider (data leakage önleme).

    Mohanty et al. 2016'da bu kritik — aynı yaprağın farklı açılarından çekilmiş
    görseller train ve test'e dağılırsa accuracy yapay olarak yüksek görünür.
    """
    train_r, val_r, _ = ratios

    groups: Dict[str, List[int]] = defaultdict(list)
    for i, f in enumerate(files):
        groups[_leaf_id_from_name(f.name)].append(i)

    leaf_ids = sorted(groups.keys())
    rng = random.Random(SEED)
    rng.shuffle(leaf_ids)

    total = len(files)
    train_target = int(total * train_r)
    val_target = int(total * val_r)

    train_idx: List[int] = []
    val_idx: List[int] = []
    test_idx: List[int] = []

    for lid in leaf_ids:
        bucket = groups[lid]
        if len(train_idx) < train_target:
            train_idx.extend(bucket)
        elif len(val_idx) < val_target:
            val_idx.extend(bucket)
        else:
            test_idx.extend(bucket)

    return train_idx, val_idx, test_idx


_SYMLINK_AVAILABLE: bool | None = None  # tek seferlik probe sonucu


def _probe_symlink_support(probe_dir: Path) -> bool:
    """Tek bir test ile symlink yetkisi olup olmadığını anlar.
    Çağıran 'symlink' modunu seçtiyse ve bu False dönerse copy'ye kalıcı geçilir."""
    probe_dir.mkdir(parents=True, exist_ok=True)
    src = probe_dir / "_probe_src.tmp"
    dst = probe_dir / "_probe_link.tmp"
    src.write_text("ok", encoding="utf-8")
    try:
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        os.symlink(src, dst)
        ok = dst.exists()
        dst.unlink()
        return ok
    except (OSError, NotImplementedError):
        return False
    finally:
        try:
            src.unlink()
        except OSError:
            pass


def place_file(src: Path, dst: Path, mode: str) -> str:
    """mode='symlink' ise tüm dosyalar için tek bir probe yapılır.
    Probe başarısız olursa kalıcı olarak copy'ye geçilir (her dosyada
    tekrar denenmez — bu Windows'ta çok yavaştır)."""
    global _SYMLINK_AVAILABLE
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return "skip"

    if mode == "symlink":
        if _SYMLINK_AVAILABLE is None:
            _SYMLINK_AVAILABLE = _probe_symlink_support(dst.parent)
            if not _SYMLINK_AVAILABLE:
                print("[INFO] Symlink yetkisi yok (Windows Geliştirici Modu kapalı?), "
                      "kalıcı olarak copy moduna geçildi.")
        if _SYMLINK_AVAILABLE:
            try:
                os.symlink(src, dst)
                return "symlink"
            except (OSError, NotImplementedError):
                _SYMLINK_AVAILABLE = False
                print("[INFO] Symlink çalışmadı, kopyalamaya geçildi.")
        shutil.copy2(src, dst)
        return "copy_fallback"

    shutil.copy2(src, dst)
    return "copy"


def validate_classes(raw_dir: Path, labels_path: Path) -> List[str]:
    if not labels_path.exists():
        print(f"[WARN] class_labels.json bulunamadı: {labels_path}")
        return []
    data = json.loads(labels_path.read_text(encoding="utf-8"))
    expected = set(data.get("classes", {}).keys())
    found = {p.name for p in raw_dir.iterdir() if p.is_dir()}
    missing = sorted(expected - found)
    extra = sorted(found - expected)
    if missing:
        print(f"[WARN] {len(missing)} sınıf eksik (raw'da bulunamadı):")
        for m in missing:
            print(f"   - {m}")
    if extra:
        print(f"[INFO] {len(extra)} ek klasör (etiket dosyasında yok):")
        for e in extra:
            print(f"   - {e}")
    return sorted(expected & found)


def main() -> int:
    parser = argparse.ArgumentParser(description="PlantVillage train/val/test split")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_SPLIT_DIR)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS_PATH)
    parser.add_argument("--ratios", type=float, nargs=3, default=(0.70, 0.15, 0.15))
    parser.add_argument("--mode", choices=["symlink", "copy"], default="symlink",
                        help="symlink: hızlı + diskten tasarruf; copy: bağımsız ama yavaş")
    parser.add_argument("--clean", action="store_true", help="out-dir varsa önce sil")
    parser.add_argument("--leaf-aware", action="store_true",
                        help="Aynı leaf_id'ye sahip görselleri tek bir split'e yerleştir "
                             "(download_dataset.py ile indirilmiş veri için ÖNERİLİR — data leakage'ı önler)")
    args = parser.parse_args()

    if not args.raw_dir.exists():
        print(f"[ERROR] Raw dataset klasörü yok: {args.raw_dir}")
        print("        PlantVillage 'color' klasörünü buraya kopyala.")
        return 1

    if sum(args.ratios) - 1.0 > 1e-6:
        print(f"[ERROR] Oranların toplamı 1.0 olmalı, verilen: {sum(args.ratios)}")
        return 1

    if args.clean and args.out_dir.exists():
        print(f"[INFO] Mevcut çıktı klasörü siliniyor: {args.out_dir}")
        shutil.rmtree(args.out_dir)

    valid_classes = validate_classes(args.raw_dir, args.labels)
    if not valid_classes:
        print(f"[WARN] Etiket eşleşmesi yapılamadı, raw'daki tüm klasörler kullanılacak.")
        valid_classes = sorted(p.name for p in args.raw_dir.iterdir() if p.is_dir())

    print(f"[INFO] {len(valid_classes)} sınıf işlenecek")
    split_mode_label = "leaf-aware (gruplu)" if args.leaf_aware else "random"
    print(f"[INFO] Mod: {args.mode}  |  Split: {split_mode_label}  |  "
          f"Oranlar: train={args.ratios[0]}, val={args.ratios[1]}, test={args.ratios[2]}")

    totals: Dict[str, int] = {"train": 0, "val": 0, "test": 0}
    per_class_counts: Dict[str, Dict[str, int]] = {}
    placement_modes: Dict[str, int] = {}

    for cls_idx, cls_name in enumerate(valid_classes, 1):
        cls_dir = args.raw_dir / cls_name
        files = collect_files(cls_dir)
        if not files:
            print(f"  ({cls_idx:2}/{len(valid_classes)}) {cls_name}: boş, atlandı")
            continue

        if args.leaf_aware:
            train_idx, val_idx, test_idx = split_indices_by_leaf(files, tuple(args.ratios))
        else:
            train_idx, val_idx, test_idx = split_indices(len(files), tuple(args.ratios))
        sets = {"train": train_idx, "val": val_idx, "test": test_idx}
        per_class_counts[cls_name] = {}

        for split_name, idx_list in sets.items():
            for i in idx_list:
                src = files[i].resolve()
                dst = args.out_dir / split_name / cls_name / files[i].name
                mode_used = place_file(src, dst, args.mode)
                placement_modes[mode_used] = placement_modes.get(mode_used, 0) + 1
            per_class_counts[cls_name][split_name] = len(idx_list)
            totals[split_name] += len(idx_list)

        print(f"  ({cls_idx:2}/{len(valid_classes)}) {cls_name}: "
              f"train={len(train_idx)}  val={len(val_idx)}  test={len(test_idx)}")

    print()
    print("=" * 60)
    print(f"TAMAMLANDI")
    print(f"  Train: {totals['train']}")
    print(f"  Val  : {totals['val']}")
    print(f"  Test : {totals['test']}")
    print(f"  Toplam: {sum(totals.values())}")
    print(f"  Dosya yerleştirme: {placement_modes}")
    print(f"  Çıktı: {args.out_dir}")
    print("=" * 60)

    manifest = {
        "ratios": list(args.ratios),
        "seed": SEED,
        "leaf_aware": bool(args.leaf_aware),
        "totals": totals,
        "num_classes": len(per_class_counts),
        "classes": list(per_class_counts.keys()),
        "per_class_counts": per_class_counts,
    }
    manifest_path = args.out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Manifest: {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
