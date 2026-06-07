"""
Test kümesinde güven eşiği analizi — PLANT_MIN_CONFIDENCE ayarı için.

Doğru/yanlış tahminlerin softmax güven ve top1-top2 marj dağılımını ölçer;
farklı eşiklerde kaç görselin reddedileceğini ve doğruluk etkisini raporlar.

Kullanım (venv-ml / torch kurulu ortam):
    python ml/confidence_threshold.py
    python ml/confidence_threshold.py --min-conf 0.55 --min-margin 0.10
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from tqdm import tqdm

ML_DIR = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT = ML_DIR / "checkpoints" / "best.pt"
DEFAULT_TEST_DIR = ML_DIR / "data" / "splits" / "test"


def build_model(num_classes: int) -> nn.Module:
    model = models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(nn.Dropout(p=0.3), nn.Linear(in_features, num_classes))
    return model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--test-dir", type=Path, default=DEFAULT_TEST_DIR)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--min-conf", type=float, default=0.60)
    parser.add_argument("--min-margin", type=float, default=0.12)
    args = parser.parse_args()

    if not args.checkpoint.exists() or not args.test_dir.exists():
        print("[ERROR] checkpoint veya test klasörü yok")
        return 1

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    classes = ckpt["classes"]
    img_size = int(ckpt.get("img_size", 224))
    mean = ckpt.get("mean", [0.485, 0.456, 0.406])
    std = ckpt.get("std", [0.229, 0.224, 0.225])

    eval_tf = transforms.Compose([
        transforms.Resize(img_size + 32),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])
    test_ds = datasets.ImageFolder(args.test_dir, transform=eval_tf)
    loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    model = build_model(len(classes)).to(device)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    conf_correct: list[float] = []
    conf_wrong: list[float] = []
    margin_correct: list[float] = []
    margin_wrong: list[float] = []

    with torch.no_grad():
        for images, targets in tqdm(loader, desc="test"):
            images = images.to(device)
            probs = torch.softmax(model(images), dim=1)
            top2 = probs.topk(2, dim=1)
            preds = top2.indices[:, 0].cpu()
            conf = top2.values[:, 0].cpu()
            margin = (top2.values[:, 0] - top2.values[:, 1]).cpu()
            for t, p, c, m in zip(targets, preds, conf, margin):
                ok = int(p) == int(t)
                (conf_correct if ok else conf_wrong).append(float(c))
                (margin_correct if ok else margin_wrong).append(float(m))

    n = len(conf_correct) + len(conf_wrong)
    acc = len(conf_correct) / n if n else 0.0

    def pct(xs: list[float], q: float) -> float:
        if not xs:
            return 0.0
        xs = sorted(xs)
        i = int(q * (len(xs) - 1))
        return xs[i]

    print(f"\n=== Güven eşiği analizi ({n} test görseli, top1 acc={acc:.4f}) ===")
    print(f"  Doğru tahmin güven:  min={pct(conf_correct,0):.3f}  p5={pct(conf_correct,0.05):.3f}  "
          f"medyan={pct(conf_correct,0.5):.3f}  p95={pct(conf_correct,0.95):.3f}")
    print(f"  Yanlış tahmin güven: min={pct(conf_wrong,0):.3f}  medyan={pct(conf_wrong,0.5):.3f}  "
          f"max={pct(conf_wrong,1):.3f}")
    print(f"  Doğru marj (top1-top2): p5={pct(margin_correct,0.05):.3f}  medyan={pct(margin_correct,0.5):.3f}")
    print(f"  Yanlış marj: medyan={pct(margin_wrong,0.5):.3f}")

    mc, mm = args.min_conf, args.min_margin
    kept = sum(
        1 for c, m, ok in zip(conf_correct + conf_wrong, margin_correct + margin_wrong,
                              [True] * len(conf_correct) + [False] * len(conf_wrong))
        if c >= mc and m >= mm
    )
    kept_correct = sum(
        1 for c, m in zip(conf_correct, margin_correct) if c >= mc and m >= mm
    )
    rejected = n - kept
    print(f"\n  Önerilen eşik: min_conf={mc}  min_margin={mm}")
    print(f"  Reddedilen: {rejected} ({100*rejected/n:.2f}%)")
    print(f"  Kabul edilen doğru: {kept_correct}/{len(conf_correct)} "
          f"({100*kept_correct/len(conf_correct):.2f}% recall doğru sınıf)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
