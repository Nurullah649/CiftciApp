"""
Test seti üzerinde modelin performansını ölç.

Çıktı:
    - Top-1, Top-3 accuracy
    - Sınıf bazında precision / recall / f1 (sklearn classification_report)
    - confusion_test.png

Kullanım:
    python ml/evaluate.py
    python ml/evaluate.py --checkpoint ml/checkpoints/best.pt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Tuple

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
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, num_classes),
    )
    return model


@torch.no_grad()
def run_eval(model: nn.Module, loader: DataLoader, device: torch.device) -> Tuple[List[int], List[int], List[int]]:
    model.eval()
    all_top1: List[int] = []
    all_top3: List[int] = []
    all_targets: List[int] = []
    for images, targets in tqdm(loader, desc="test"):
        images = images.to(device, non_blocking=True)
        targets_cpu = targets.tolist()
        outputs = model(images)
        top3 = outputs.topk(k=3, dim=1).indices.cpu().tolist()
        for t, row in zip(targets_cpu, top3):
            all_top1.append(row[0])
            all_top3.append(1 if t in row else 0)
            all_targets.append(t)
    return all_top1, all_top3, all_targets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--test-dir", type=Path, default=DEFAULT_TEST_DIR)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=4)
    args = parser.parse_args()

    if not args.checkpoint.exists():
        print(f"[ERROR] Checkpoint yok: {args.checkpoint}")
        return 1
    if not args.test_dir.exists():
        print(f"[ERROR] Test klasörü yok: {args.test_dir}")
        return 1

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    classes = ckpt["classes"]
    mean = ckpt.get("mean", [0.485, 0.456, 0.406])
    std = ckpt.get("std", [0.229, 0.224, 0.225])
    img_size = ckpt.get("img_size", 224)

    eval_tf = transforms.Compose([
        transforms.Resize(img_size + 32),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])
    test_ds = datasets.ImageFolder(args.test_dir, transform=eval_tf)
    if test_ds.classes != classes:
        print("[WARN] Test klasör sırası checkpoint ile aynı değil, yeniden eşleştiriliyor.")

    loader = DataLoader(
        test_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True,
    )

    model = build_model(num_classes=len(classes)).to(device)
    model.load_state_dict(ckpt["state_dict"])

    top1, top3, targets = run_eval(model, loader, device)
    n = len(targets)
    top1_acc = sum(int(p == t) for p, t in zip(top1, targets)) / n
    top3_acc = sum(top3) / n
    print(f"\n=== Test Sonuçları ({n} görsel) ===")
    print(f"  Top-1 Accuracy: {top1_acc:.4f}")
    print(f"  Top-3 Accuracy: {top3_acc:.4f}")

    try:
        from sklearn.metrics import classification_report, confusion_matrix
        idx_to_class = test_ds.classes
        print("\nSınıf bazında rapor:")
        print(classification_report(
            targets, top1,
            labels=list(range(len(idx_to_class))),
            target_names=idx_to_class,
            digits=3,
            zero_division=0,
        ))

        report_dict = classification_report(
            targets, top1,
            labels=list(range(len(idx_to_class))),
            target_names=idx_to_class,
            output_dict=True,
            zero_division=0,
        )
        report_path = args.checkpoint.parent / "test_report.json"
        report_path.write_text(json.dumps({
            "top1_accuracy": top1_acc,
            "top3_accuracy": top3_acc,
            "per_class": report_dict,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[INFO] Rapor kaydedildi: {report_path}")

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            cm = confusion_matrix(targets, top1, labels=list(range(len(idx_to_class))))
            fig, ax = plt.subplots(figsize=(14, 12))
            im = ax.imshow(cm, cmap="Blues")
            ax.set_xticks(range(len(idx_to_class)))
            ax.set_yticks(range(len(idx_to_class)))
            ax.set_xticklabels(idx_to_class, rotation=90, fontsize=6)
            ax.set_yticklabels(idx_to_class, fontsize=6)
            ax.set_xlabel("Pred")
            ax.set_ylabel("True")
            ax.set_title(f"Test Confusion Matrix (top1={top1_acc:.3f})")
            plt.colorbar(im, ax=ax)
            fig.tight_layout()
            out = args.checkpoint.parent / "confusion_test.png"
            fig.savefig(out, dpi=150)
            plt.close(fig)
            print(f"[INFO] Confusion matrix: {out}")
        except Exception as e:
            print(f"[WARN] Plot oluşturulamadı: {e}")
    except ImportError:
        print("[INFO] sklearn yok, sadece accuracy verildi.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
