"""PlantDoc dataset downloader & integrator.

Kaynak: LamTNguyen/PlantDoc (HuggingFace) — PlantDoc.zip (992 MB)
   Orijinal: pratikkayal/PlantDoc-Dataset (GitHub)
   Paper: arXiv:1911.10317 (Singh et al. 2020)

İçerik: 2598 görsel, 27 sınıf (13 bitki × ortalama 2 varyant)
        Saha koşullarında çekilmiş — laboratuvar değil, gerçek arka plan + ışık.

Bu modül:
    1. PlantDoc.zip'i HF Hub'dan indirir
    2. ml/data/external/plantdoc/ altına extract eder
    3. Sınıfları birleşik taksonomiye eşler (CLASS_MAP)
    4. ml/data/raw/<unified>/plantdoc__xxx.jpg formatında entegre eder

Kullanım:
    python -m ml.datasets.plantdoc                  # tam pipeline
    python -m ml.datasets.plantdoc --download-only  # sadece indir
    python -m ml.datasets.plantdoc --integrate-only # sadece raw'a entegre et
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Module import için fallback
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent))

from ml.datasets import (
    DEFAULT_EXTERNAL_DIR,
    DEFAULT_RAW_DIR,
    extract_zip,
    list_images,
    list_images_recursive,
    merge_into_raw,
    print_step,
    safe_dirname,
)

PLANTDOC_REPO = "LamTNguyen/PlantDoc"
PLANTDOC_FILE = "PlantDoc.zip"
EXTERNAL_NAME = "plantdoc"


# PlantDoc sınıfları → birleşik PlantVillage taksonomisi.
# Sol: normalize edilmiş anahtar (boşluk/alt çizgi/case farketmez — normalize_class_name fn'i kullanılır)
# Sağ: birleşik isim
CLASS_MAP = {
    # Apple
    "apple_scab_leaf":                                   "Apple___Apple_scab",
    "apple_leaf":                                        "Apple___healthy",
    "apple_rust_leaf":                                   "Apple___Cedar_apple_rust",

    # Bell pepper
    "bell_pepper_leaf":                                  "Pepper,_bell___healthy",
    "bell_pepper_leaf_spot":                             "Pepper,_bell___Bacterial_spot",

    # Blueberry
    "blueberry_leaf":                                    "Blueberry___healthy",

    # Cherry
    "cherry_leaf":                                       "Cherry_(including_sour)___healthy",

    # Corn
    "corn_gray_leaf_spot":                               "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "corn_leaf_blight":                                  "Corn_(maize)___Northern_Leaf_Blight",
    "corn_rust_leaf":                                    "Corn_(maize)___Common_rust_",

    # Grape
    "grape_leaf":                                        "Grape___healthy",
    "grape_leaf_black_rot":                              "Grape___Black_rot",

    # Peach
    "peach_leaf":                                        "Peach___healthy",

    # Potato
    "potato_leaf_early_blight":                          "Potato___Early_blight",
    "potato_leaf_late_blight":                           "Potato___Late_blight",
    "potato_leaf":                                       "Potato___healthy",

    # Raspberry
    "raspberry_leaf":                                    "Raspberry___healthy",

    # Soybean (PlantDoc'ta hem "Soyabean" hem "Soybean")
    "soyabean_leaf":                                     "Soybean___healthy",
    "soybean_leaf":                                      "Soybean___healthy",

    # Squash
    "squash_powdery_mildew_leaf":                        "Squash___Powdery_mildew",

    # Strawberry
    "strawberry_leaf":                                   "Strawberry___healthy",

    # Tomato — PlantDoc çok varyant içeriyor
    "tomato_leaf":                                       "Tomato___healthy",
    "tomato_leaf_bacterial_spot":                        "Tomato___Bacterial_spot",
    "tomato_leaf_late_blight":                           "Tomato___Late_blight",
    "tomato_leaf_mosaic_virus":                          "Tomato___Tomato_mosaic_virus",
    "tomato_leaf_yellow_virus":                          "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "tomato_mold_leaf":                                  "Tomato___Leaf_Mold",
    "tomato_septoria_leaf_spot":                         "Tomato___Septoria_leaf_spot",
    "tomato_two_spotted_spider_mites_leaf":              "Tomato___Spider_mites Two-spotted_spider_mite",
    "tomato_early_blight_leaf":                          "Tomato___Early_blight",
}


def normalize_class_name(name: str) -> str:
    """Boşluk/alt çizgi/case farkını eler — eşleştirme için anahtar üretir."""
    s = name.strip().lower()
    s = s.replace(" ", "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s


def download_plantdoc(
    out_dir: Path = DEFAULT_EXTERNAL_DIR / EXTERNAL_NAME,
    force: bool = False,
) -> Path:
    """PlantDoc.zip'i indir + extract et."""
    print_step("PlantDoc indirme & extract")

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[HATA] huggingface_hub gerekli: pip install huggingface_hub")
        raise SystemExit(1)

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    print(f"  [HF] {PLANTDOC_REPO}/{PLANTDOC_FILE} indiriliyor (ilk seferde ~992 MB)...")
    zip_path = Path(hf_hub_download(
        repo_id=PLANTDOC_REPO,
        repo_type="dataset",
        filename=PLANTDOC_FILE,
    ))
    print(f"  [HF] Önbellek yolu: {zip_path}")
    print(f"  [HF] Boyut: {zip_path.stat().st_size / (1024*1024):.1f} MB")

    extract_dir = out_dir
    extract_dir.mkdir(parents=True, exist_ok=True)
    flag = extract_dir / ".extracted"
    if flag.exists() and not force:
        files_in = list_images_recursive(extract_dir)
        if files_in:
            print(f"  [SKIP] Daha önce extract edilmiş: {len(files_in)} dosya")
            return extract_dir

    print(f"  [EXT] Extract ediliyor: {extract_dir}")
    n = extract_zip(zip_path, extract_dir)
    flag.write_text("ok", encoding="utf-8")
    print(f"  [EXT] {n} dosya extract edildi.")
    return extract_dir


def find_class_dirs(root: Path) -> dict:
    """root altında her seviyede 'train/<class>' veya '<class>/' klasörlerini bul.

    PlantDoc orijinal yapısı:
        train/<class>/*.jpg
        test/<class>/*.jpg
    """
    out = {}
    for split_dir in [root, root / "train", root / "test"]:
        if not split_dir.exists():
            continue
        for sub in sorted(split_dir.iterdir()):
            if not sub.is_dir():
                continue
            imgs = list_images(sub)
            if imgs:
                key = (sub.name, "train" if "train" in str(split_dir) else "test")
                if sub.name in out:
                    out[sub.name].extend(imgs)
                else:
                    out[sub.name] = list(imgs)

    for sub in sorted(root.iterdir()) if root.exists() else []:
        if not sub.is_dir() or sub.name in {"train", "test", "__MACOSX"}:
            continue
        imgs = list_images(sub)
        if imgs and sub.name not in out:
            out[sub.name] = imgs

    return out


def integrate_plantdoc(
    extracted_dir: Path,
    raw_dir: Path = DEFAULT_RAW_DIR,
    validate: bool = True,
) -> dict:
    """PlantDoc'tan görselleri birleşik raw/'a kopyala."""
    print_step("PlantDoc -> raw/ entegrasyonu")

    pd_classes = find_class_dirs(extracted_dir)
    if not pd_classes:
        print(f"  [HATA] {extracted_dir} altında sınıf klasörü bulunamadı.")
        return {}

    print(f"  [INFO] PlantDoc'ta bulunan {len(pd_classes)} sınıf:")

    stats = {"mapped": 0, "unmapped": 0, "written": 0, "invalid": 0, "new_classes": []}
    name_w = max(len(n) for n in pd_classes) if pd_classes else 30

    for pd_class in sorted(pd_classes):
        pd_class_norm = normalize_class_name(pd_class)
        unified = CLASS_MAP.get(pd_class_norm)
        imgs = pd_classes[pd_class]

        if unified is None:
            crop_guess = pd_class_norm.split()[0].strip().title()
            unified = f"{crop_guess}___PlantDoc_unmapped_{safe_dirname(pd_class_norm)}"
            stats["unmapped"] += 1
            stats["new_classes"].append((pd_class_norm, unified))
            tag = "YENI"
        else:
            stats["mapped"] += 1
            tag = "MAP"

        written, invalid = merge_into_raw(
            source="plantdoc",
            source_class=pd_class_norm,
            unified_class=unified,
            images=imgs,
            raw_dir=raw_dir,
            validate=validate,
        )
        stats["written"] += written
        stats["invalid"] += invalid
        print(f"  [{tag:>5}] {pd_class_norm[:name_w].ljust(name_w)} ({len(imgs):>4} img) -> {unified}  "
              f"[w={written} inv={invalid}]")

    print()
    print(f"  Toplam yazılan : {stats['written']}")
    print(f"  Bozuk görsel   : {stats['invalid']}")
    print(f"  Eşlenen sınıf  : {stats['mapped']}")
    print(f"  Eşlenmeyen     : {stats['unmapped']}")
    if stats["new_classes"]:
        print()
        print("  YENİ EKLENEN SINIFLAR (class_labels.json güncellemen gerek):")
        for src, uni in stats["new_classes"]:
            print(f"    {src} -> {uni}")

    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-only", action="store_true", help="Sadece indir/extract, raw'a entegre etme")
    parser.add_argument("--integrate-only", action="store_true", help="Sadece raw'a entegre et (zaten extract edilmiş)")
    parser.add_argument("--external-dir", type=Path, default=DEFAULT_EXTERNAL_DIR / EXTERNAL_NAME)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--force", action="store_true", help="Tekrar extract et")
    parser.add_argument("--no-validate", action="store_true", help="PIL validation atla (hızlı)")
    args = parser.parse_args()

    if args.integrate_only:
        ext_dir = args.external_dir
        if not ext_dir.exists():
            print(f"[HATA] {ext_dir} yok. Önce --download-only çalıştır.")
            return 1
    else:
        ext_dir = download_plantdoc(args.external_dir, force=args.force)

    if not args.download_only:
        integrate_plantdoc(ext_dir, args.raw_dir, validate=not args.no_validate)

    print()
    print("[DONE] PlantDoc entegrasyonu tamamlandı.")
    print("       Sonraki: python -m ml.datasets.olive")
    print("       veya:    python ml/integrate_dataset.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
