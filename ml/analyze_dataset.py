"""
Hibrit dataset detaylı analiz scripti.

İndirilmiş `ml/data/raw/` ve `ml/data/splits/` üzerinde:
    - Sınıf başına görsel sayısı (raw + train/val/test)
    - Kaynak dağılımı (PlantVillage / PlantDoc / Olive / Wheat / Cotton / Sunflower)
    - Bitki (crop) bazında dağılım
    - Hastalık statüsü (healthy/warning/critical) bazında dağılım
    - Class imbalance metrikleri (min/max oran, Gini, entropy)
    - leaf_id istatistikleri (kaç benzersiz yaprak, görsel/yaprak oranı — sadece PV)
    - Görsel boyutu ve dosya boyutu örneklem analizi
    - Leak kontrolü (aynı leaf_id birden fazla split'te var mı?)

Kullanım:
    python ml/analyze_dataset.py
    python ml/analyze_dataset.py --plot       # PNG grafik üret
    python ml/analyze_dataset.py --out raporu.json

Bitirme raporu için ideal — bütün rakamlar JSON olarak da kaydedilir.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ML_DIR = Path(__file__).resolve().parent
DEFAULT_RAW = ML_DIR / "data" / "raw"
DEFAULT_SPLITS = ML_DIR / "data" / "splits"
DEFAULT_LABELS = ML_DIR / "class_labels.json"
VALID_EXT = {".jpg", ".jpeg", ".png"}


def list_images(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    return [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VALID_EXT]


SOURCE_PREFIXES = ("plantdoc__", "olive__", "wheat__", "cotton__", "sunflower__")


def _detect_source(filename: str) -> str:
    """Dosya adından kaynak prefix'ini çıkar."""
    n = filename.lower()
    for prefix in SOURCE_PREFIXES:
        if n.startswith(prefix):
            return prefix.rstrip("_")
    return "plantvillage"


def _leaf_id_from_name(name: str) -> str:
    base = name.rsplit(".", 1)[0]
    if "__" in base:
        return base.rsplit("__", 1)[0]
    return base


def count_per_class(root: Path) -> Dict[str, int]:
    out: Dict[str, int] = {}
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        out[d.name] = len(list_images(d))
    return out


def collect_leaf_ids(root: Path) -> Dict[str, List[str]]:
    """{class_name: [leaf_id, leaf_id, ...]} — duplicate'lı (her görsel için bir kayıt)."""
    out: Dict[str, List[str]] = {}
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        out[d.name] = [_leaf_id_from_name(f.name) for f in list_images(d)]
    return out


def gini_index(counts: List[int]) -> float:
    """Class imbalance için Gini indeksi. 0 = mükemmel dengeli, 1 = tek sınıfta hepsi."""
    if not counts:
        return 0.0
    s = sorted(counts)
    n = len(s)
    total = sum(s)
    if total == 0:
        return 0.0
    cum = 0.0
    for i, v in enumerate(s, 1):
        cum += i * v
    return (2 * cum) / (n * total) - (n + 1) / n


def entropy_normalized(counts: List[int]) -> float:
    """0..1 arası normalize edilmiş entropi. 1 = mükemmel dengeli."""
    total = sum(counts)
    if total <= 0:
        return 0.0
    probs = [c / total for c in counts if c > 0]
    h = -sum(p * math.log(p) for p in probs)
    h_max = math.log(len(probs)) if len(probs) > 1 else 1.0
    return h / h_max if h_max > 0 else 0.0


def sample_image_metadata(folder: Path, sample_size: int = 10) -> List[dict]:
    """Sınıftan birkaç görsel seçip boyut ve dosya boyutu bilgisi al."""
    try:
        from PIL import Image
    except ImportError:
        return []
    files = list_images(folder)
    if not files:
        return []
    rng = random.Random(42)
    picks = rng.sample(files, min(sample_size, len(files)))
    info = []
    for p in picks:
        try:
            with Image.open(p) as img:
                info.append({
                    "file": p.name,
                    "width": img.width,
                    "height": img.height,
                    "mode": img.mode,
                    "size_kb": round(p.stat().st_size / 1024, 1),
                })
        except Exception:
            continue
    return info


def fmt_int(x: int) -> str:
    return f"{x:,}".replace(",", ".")


def print_header(title: str, char: str = "=", width: int = 78) -> None:
    print()
    print(char * width)
    print(f"  {title}")
    print(char * width)


def analyze(
    raw_dir: Path,
    splits_dir: Path,
    labels_path: Path,
    out_json: Optional[Path],
    plot: bool,
) -> int:
    labels_meta: Dict[str, dict] = {}
    if labels_path.exists():
        labels_data = json.loads(labels_path.read_text(encoding="utf-8"))
        labels_meta = labels_data.get("classes", {})

    raw_counts = count_per_class(raw_dir)
    train_counts = count_per_class(splits_dir / "train")
    val_counts = count_per_class(splits_dir / "val")
    test_counts = count_per_class(splits_dir / "test")

    if not raw_counts and not train_counts:
        print(f"[ERROR] Ne raw ne de splits klasörü bulundu.\n"
              f"        raw   : {raw_dir}\n"
              f"        splits: {splits_dir}")
        return 1

    total_raw = sum(raw_counts.values())
    total_train = sum(train_counts.values())
    total_val = sum(val_counts.values())
    total_test = sum(test_counts.values())

    source_per_class: Dict[str, Counter] = {}
    if raw_dir.exists():
        for d in sorted(raw_dir.iterdir()):
            if not d.is_dir():
                continue
            cnt = Counter(_detect_source(p.name) for p in list_images(d))
            if cnt:
                source_per_class[d.name] = cnt

    total_per_source: Counter = Counter()
    for cnt in source_per_class.values():
        total_per_source.update(cnt)

    print_header("HIBRIT DATASET ANALIZ RAPORU")
    print(f"  Raw dir    : {raw_dir}  ({fmt_int(total_raw)} görsel, {len(raw_counts)} sınıf)")
    print(f"  Splits dir : {splits_dir}")
    print(f"               train={fmt_int(total_train)}  val={fmt_int(total_val)}  test={fmt_int(total_test)}")
    if total_raw > 0:
        print(f"               {total_train/total_raw*100:.1f}% / {total_val/total_raw*100:.1f}% / {total_test/total_raw*100:.1f}%")

    if total_per_source:
        print()
        print(f"  Kaynak basina:")
        for src in ["plantvillage", "plantdoc", "olive", "wheat", "cotton", "sunflower"]:
            n = total_per_source.get(src, 0)
            if n > 0:
                pct = n / total_raw * 100 if total_raw else 0
                print(f"    {src:<13s}: {fmt_int(n):>8}  ({pct:5.1f}%)")

    print_header("1. SINIF BAZINDA GORSEL SAYISI", "-")
    classes_sorted = sorted(set(list(raw_counts) + list(train_counts)))
    name_w = max(len(c) for c in classes_sorted) if classes_sorted else 20
    name_w = min(name_w, 50)
    print(f"  {'#':>3}  {'Sinif'.ljust(name_w)}  {'Raw':>7}  {'Train':>6}  {'Val':>5}  {'Test':>5}  {'Status':>8}")
    print("  " + "-" * (3 + 2 + name_w + 2 + 7 + 2 + 6 + 2 + 5 + 2 + 5 + 2 + 8))
    for i, c in enumerate(classes_sorted, 1):
        status = labels_meta.get(c, {}).get("status", "?")
        print(f"  {i:>3}  {c[:name_w].ljust(name_w)}  "
              f"{raw_counts.get(c, 0):>7,}  {train_counts.get(c, 0):>6,}  "
              f"{val_counts.get(c, 0):>5,}  {test_counts.get(c, 0):>5,}  {status:>8}")

    print_header("1b. KAYNAK BAZINDA SINIF DAGILIMI (saha kalitesi)", "-")
    if source_per_class:
        mixed = [(c, cnt) for c, cnt in source_per_class.items() if len(cnt) > 1]
        if mixed:
            print(f"  {'Sinif'.ljust(min(name_w, 50))}  {'PV':>5}  {'PD':>4}  {'Olive':>5}  {'Wheat':>5}  {'Cot':>4}  {'Sun':>4}  {'%Saha':>6}")
            print("  " + "-" * (min(name_w, 50) + 2 + 5 + 2 + 4 + 2 + 5 + 2 + 5 + 2 + 4 + 2 + 4 + 2 + 6))
            for c, cnt in sorted(mixed, key=lambda x: -sum(v for k, v in x[1].items() if k != "plantvillage")):
                pv = cnt.get("plantvillage", 0)
                pd = cnt.get("plantdoc", 0)
                ol = cnt.get("olive", 0)
                wh = cnt.get("wheat", 0)
                co = cnt.get("cotton", 0)
                su = cnt.get("sunflower", 0)
                tot = pv + pd + ol + wh + co + su
                non_pv = tot - pv
                pct_field = non_pv / tot * 100 if tot else 0
                cdisp = c[:50]
                print(f"  {cdisp:<{min(name_w, 50)}}  {pv:>5}  {pd:>4}  {ol:>5}  {wh:>5}  {co:>4}  {su:>4}  {pct_field:>5.1f}%")
            print(f"  ... (sadece birden fazla kaynak olan {len(mixed)} sınıf gösterildi)")
        else:
            print("  (Tüm sınıflar tek kaynaktan.)")

    print_header("2. BITKI (CROP) BAZINDA DAGILIM", "-")
    crop_totals: Dict[str, int] = defaultdict(int)
    crop_classes: Dict[str, int] = defaultdict(int)
    crop_diseases: Dict[str, int] = defaultdict(int)
    for c, n in raw_counts.items():
        meta = labels_meta.get(c, {})
        crop = meta.get("crop") or c.split("___", 1)[0]
        crop_totals[crop] += n
        crop_classes[crop] += 1
        if "healthy" not in c.lower():
            crop_diseases[crop] += 1
    print(f"  {'Crop':<25}  {'Sinif':>5}  {'Hastalik':>8}  {'Gorsel':>8}  {'%':>5}")
    print("  " + "-" * 56)
    for crop in sorted(crop_totals, key=lambda x: -crop_totals[x]):
        n = crop_totals[crop]
        pct = n / total_raw * 100 if total_raw else 0
        print(f"  {crop:<25}  {crop_classes[crop]:>5}  {crop_diseases[crop]:>8}  {n:>8,}  {pct:>4.1f}%")
    print(f"  {'TOPLAM':<25}  {sum(crop_classes.values()):>5}  "
          f"{sum(crop_diseases.values()):>8}  {total_raw:>8,}  100.0%")

    print_header("3. HASTALIK STATUSU BAZINDA DAGILIM", "-")
    status_totals: Dict[str, int] = defaultdict(int)
    status_classes: Dict[str, int] = defaultdict(int)
    for c, n in raw_counts.items():
        st = labels_meta.get(c, {}).get("status", "?")
        status_totals[st] += n
        status_classes[st] += 1
    print(f"  {'Status':<12}  {'Sinif':>5}  {'Gorsel':>8}  {'%':>5}")
    print("  " + "-" * 38)
    for st in sorted(status_totals, key=lambda x: -status_totals[x]):
        n = status_totals[st]
        pct = n / total_raw * 100 if total_raw else 0
        print(f"  {st:<12}  {status_classes[st]:>5}  {n:>8,}  {pct:>4.1f}%")

    print_header("4. CLASS IMBALANCE METRIKLERI", "-")
    counts = list(raw_counts.values())
    if counts:
        sorted_counts = sorted(counts)
        min_c, max_c = sorted_counts[0], sorted_counts[-1]
        median = sorted_counts[len(sorted_counts) // 2]
        mean = sum(counts) / len(counts)
        gini = gini_index(counts)
        ent = entropy_normalized(counts)
        ratio = max_c / min_c if min_c > 0 else float("inf")

        min_cls = min(raw_counts, key=lambda k: raw_counts[k])
        max_cls = max(raw_counts, key=lambda k: raw_counts[k])

        print(f"  Min görsel sayısı   : {min_c:>5}  ({min_cls})")
        print(f"  Max görsel sayısı   : {max_c:>5}  ({max_cls})")
        print(f"  Ortalama            : {mean:>5.0f}")
        print(f"  Medyan              : {median:>5}")
        print(f"  Max/Min oranı       : {ratio:>5.1f}x   -> {'DENGESIZ' if ratio > 10 else 'OK'}")
        print(f"  Gini indeksi        : {gini:>5.3f}   (0=dengeli, 1=tek sinifta toplanmis)")
        print(f"  Normalize entropy   : {ent:>5.3f}   (1.0=mukemmel dengeli)")
        print()
        print("  YORUM:")
        if ratio > 30:
            print("    Çok dengesiz → class weights veya oversampling ZORUNLU.")
        elif ratio > 10:
            print("    Dengesiz → class weights önerilir (sqrt veya effective scheme).")
        else:
            print("    Yeterince dengeli → class weights opsiyonel.")

    print_header("5. LEAF GROUPING ISTATISTIKLERI (sadece PlantVillage'da gecerli)", "-")
    if raw_dir.exists():
        pv_imgs = 0
        pv_leaves: set = set()
        for d in raw_dir.iterdir():
            if not d.is_dir():
                continue
            for p in list_images(d):
                if _detect_source(p.name) == "plantvillage":
                    pv_imgs += 1
                    pv_leaves.add(_leaf_id_from_name(p.name))
        if pv_imgs > 0:
            print(f"  PlantVillage görseller    : {pv_imgs:,}")
            print(f"  Benzersiz yaprak (PV)     : {len(pv_leaves):,}")
            print(f"  Ortalama görsel/yaprak    : {pv_imgs/max(len(pv_leaves), 1):.2f}")
            print()
            print("  PV için leaf-aware split SART (aynı yaprak farklı açılardan çekilmiş).")
            print("  PD/Olive/Wheat/Cotton/Sunflower için leaf_id yok → stratified random fallback.")
        else:
            print("  PlantVillage görselleri tespit edilemedi.")

    leak_count = 0
    if (splits_dir / "train").exists():
        train_leaves = defaultdict(set)
        val_leaves = defaultdict(set)
        test_leaves = defaultdict(set)
        for c in classes_sorted:
            train_leaves[c] = {_leaf_id_from_name(p.name) for p in list_images(splits_dir / "train" / c)}
            val_leaves[c] = {_leaf_id_from_name(p.name) for p in list_images(splits_dir / "val" / c)}
            test_leaves[c] = {_leaf_id_from_name(p.name) for p in list_images(splits_dir / "test" / c)}
            overlap_tv = train_leaves[c] & val_leaves[c]
            overlap_tt = train_leaves[c] & test_leaves[c]
            overlap_vt = val_leaves[c] & test_leaves[c]
            leak_count += len(overlap_tv) + len(overlap_tt) + len(overlap_vt)

        print_header("6. LEAK KONTROLU (train/val/test arasinda ortak leaf_id)", "-")
        print(f"  Toplam ortak leaf_id sayisi : {leak_count}")
        if leak_count == 0:
            print("  [OK] Split temiz - hicbir yaprak birden fazla split'te yok.")
        else:
            print("  [UYARI] Aynı yaprak birden fazla split'te! Leaf-aware split tekrar calistirilmali.")

    print_header("7. ORNEK GORSEL METADATASI", "-")
    sample_class = classes_sorted[0] if classes_sorted else None
    if sample_class:
        info = sample_image_metadata(raw_dir / sample_class, sample_size=5)
        if info:
            print(f"  Ornek sinif: {sample_class}")
            widths = [d["width"] for d in info]
            heights = [d["height"] for d in info]
            sizes = [d["size_kb"] for d in info]
            modes = Counter(d["mode"] for d in info)
            print(f"    Genislik (px) : min={min(widths)}, max={max(widths)}, ort={sum(widths)//len(widths)}")
            print(f"    Yukseklik (px): min={min(heights)}, max={max(heights)}, ort={sum(heights)//len(heights)}")
            print(f"    Dosya (KB)    : min={min(sizes):.1f}, max={max(sizes):.1f}, ort={sum(sizes)/len(sizes):.1f}")
            print(f"    Renk modu     : {dict(modes)}")

    if out_json:
        payload = {
            "summary": {
                "total_raw": total_raw,
                "total_train": total_train,
                "total_val": total_val,
                "total_test": total_test,
                "num_classes": len(raw_counts),
            },
            "per_class": {
                c: {
                    "raw": raw_counts.get(c, 0),
                    "train": train_counts.get(c, 0),
                    "val": val_counts.get(c, 0),
                    "test": test_counts.get(c, 0),
                    "status": labels_meta.get(c, {}).get("status"),
                    "crop": labels_meta.get(c, {}).get("crop"),
                    "tr": labels_meta.get(c, {}).get("tr"),
                } for c in classes_sorted
            },
            "per_crop": dict(crop_totals),
            "per_status": dict(status_totals),
            "imbalance": {
                "min": min(counts) if counts else 0,
                "max": max(counts) if counts else 0,
                "ratio_max_over_min": max(counts) / min(counts) if counts and min(counts) else None,
                "gini": gini_index(counts) if counts else 0,
                "normalized_entropy": entropy_normalized(counts) if counts else 0,
            },
            "leak_count": leak_count,
        }
        out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print()
        print(f"[INFO] JSON rapor kaydedildi: {out_json}")

    if plot:
        plot_distribution(raw_counts, train_counts, val_counts, test_counts, ML_DIR)

    print()
    return 0


def plot_distribution(
    raw_counts: Dict[str, int],
    train_counts: Dict[str, int],
    val_counts: Dict[str, int],
    test_counts: Dict[str, int],
    out_dir: Path,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[WARN] matplotlib yok, grafik atlandi (pip install matplotlib).")
        return

    classes = sorted(raw_counts, key=lambda k: -raw_counts[k])
    n = list(range(len(classes)))
    raw_v = [raw_counts.get(c, 0) for c in classes]
    train_v = [train_counts.get(c, 0) for c in classes]
    val_v = [val_counts.get(c, 0) for c in classes]
    test_v = [test_counts.get(c, 0) for c in classes]

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.bar(n, train_v, label="train", color="#1f77b4")
    ax.bar(n, val_v, bottom=train_v, label="val", color="#ff7f0e")
    ax.bar(n, test_v, bottom=[a + b for a, b in zip(train_v, val_v)], label="test", color="#2ca02c")
    ax.set_xticks(n)
    ax.set_xticklabels(classes, rotation=90, fontsize=7)
    ax.set_ylabel("Görsel sayısı")
    ax.set_title("PlantVillage — sınıf başına görsel dağılımı (train/val/test)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out_path = out_dir / "class_distribution.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[INFO] Grafik kaydedildi: {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--splits", type=Path, default=DEFAULT_SPLITS)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--out", type=Path, default=None,
                        help="JSON rapor çıktısı (ör: ml/dataset_report.json)")
    parser.add_argument("--plot", action="store_true",
                        help="ml/class_distribution.png üret (matplotlib gerekir)")
    args = parser.parse_args()
    return analyze(args.raw, args.splits, args.labels, args.out, args.plot)


if __name__ == "__main__":
    raise SystemExit(main())
