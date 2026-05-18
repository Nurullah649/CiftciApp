"""
Hızlı dataset doğrulama scripti.

Verilen klasördeki sınıfları ve görsel sayılarını
ml/class_labels.json ile karşılaştırır.

Kullanım:
    python ml/verify_dataset.py "C:\\Users\\agdbe\\Desktop\\plantvillage dataset\\color"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VALID_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
ML_DIR = Path(__file__).resolve().parent
DEFAULT_LABELS = ML_DIR / "class_labels.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path, help="38 sınıf klasörünü barındıran dizin")
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"[HATA] Dizin yok: {args.data_dir}")
        return 1

    expected = set()
    if args.labels.exists():
        labels = json.loads(args.labels.read_text(encoding="utf-8"))
        expected = set(labels.get("classes", {}).keys())

    found_dirs = sorted(p for p in args.data_dir.iterdir() if p.is_dir())
    found_names = {p.name for p in found_dirs}

    print(f"\n{'='*70}")
    print(f"DATASET: {args.data_dir}")
    print(f"{'='*70}")
    print(f"Klasor sayisi : {len(found_dirs)}")
    print(f"Beklenen      : {len(expected)} (class_labels.json'dan)")
    print()

    total_images = 0
    rows = []
    for d in found_dirs:
        files = [f for f in d.iterdir() if f.is_file() and f.suffix.lower() in VALID_EXT]
        in_labels = "OK" if d.name in expected else "EKSTRA"
        rows.append((d.name, len(files), in_labels))
        total_images += len(files)

    name_w = max(len(r[0]) for r in rows)
    print(f"{'#':>3}  {'Sinif'.ljust(name_w)}  {'Gorsel':>7}  Durum")
    print("-" * (3 + 2 + name_w + 2 + 7 + 2 + 10))
    for i, (name, count, status) in enumerate(rows, 1):
        print(f"{i:>3}  {name.ljust(name_w)}  {count:>7}  {status}")

    print("-" * (3 + 2 + name_w + 2 + 7 + 2 + 10))
    print(f"{'':>3}  {'TOPLAM'.ljust(name_w)}  {total_images:>7}")
    print()

    missing = sorted(expected - found_names) if expected else []
    extra = sorted(found_names - expected) if expected else []

    if missing:
        print(f"[EKSIK] class_labels.json'da var ama klasorde yok ({len(missing)}):")
        for m in missing:
            print(f"   - {m}")
    if extra:
        print(f"[EKSTRA] Klasorde var ama class_labels.json'da yok ({len(extra)}):")
        for e in extra:
            print(f"   - {e}")
    if expected and not missing and not extra:
        print("[OK] Klasor adlari class_labels.json ile %100 ortusuyor.")

    counts = [r[1] for r in rows]
    if counts:
        print(f"\nSinif basina gorsel istatistigi:")
        print(f"   min: {min(counts)}  |  max: {max(counts)}  |  ortalama: {sum(counts)//len(counts)}")
        if min(counts) < 200:
            print(f"   [UYARI] Bazi siniflar 200'den az gorsel iceriyor, dengesizlik olabilir.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
