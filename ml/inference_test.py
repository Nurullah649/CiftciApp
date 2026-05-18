"""
Eğitilmiş modeli tek bir görsel üzerinde dene.

Backend entegrasyonundan önce modelin sağlıklı çalıştığını doğrulamak içindir.
class_labels.json'daki Türkçe ad ve öneriyi de birlikte yazdırır
(böylece backend yanıtının nasıl görüneceğini tahmin edebilirsin).

Kullanım:
    python ml/inference_test.py path/to/leaf.jpg
    python ml/inference_test.py path/to/leaf.jpg --topk 5
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import models, transforms

ML_DIR = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT = ML_DIR / "checkpoints" / "best.pt"
DEFAULT_LABELS = ML_DIR / "class_labels.json"


def build_model(num_classes: int) -> nn.Module:
    model = models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, num_classes),
    )
    return model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path, help="Test edilecek görsel yolu")
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--topk", type=int, default=3)
    args = parser.parse_args()

    if not args.image.exists():
        print(f"[ERROR] Görsel bulunamadı: {args.image}")
        return 1
    if not args.checkpoint.exists():
        print(f"[ERROR] Checkpoint bulunamadı: {args.checkpoint}")
        return 1

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    classes = ckpt["classes"]
    mean = ckpt.get("mean", [0.485, 0.456, 0.406])
    std = ckpt.get("std", [0.229, 0.224, 0.225])
    img_size = ckpt.get("img_size", 224)

    tf = transforms.Compose([
        transforms.Resize(img_size + 32),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])

    img = Image.open(args.image).convert("RGB")
    tensor = tf(img).unsqueeze(0).to(device)

    model = build_model(num_classes=len(classes)).to(device)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    with torch.no_grad():
        logits = model(tensor)
        probs = F.softmax(logits, dim=1)[0]
        topk = probs.topk(k=min(args.topk, len(classes)))

    labels_map = {}
    if args.labels.exists():
        labels_map = json.loads(args.labels.read_text(encoding="utf-8")).get("classes", {})

    print(f"\n=== Tahmin: {args.image.name} ===")
    for rank, (idx, p) in enumerate(zip(topk.indices.tolist(), topk.values.tolist()), 1):
        cls_id = classes[idx]
        meta = labels_map.get(cls_id, {})
        tr_name = meta.get("tr", cls_id)
        status = meta.get("status", "unknown")
        print(f"  {rank}. [{p*100:6.2f}%]  {tr_name}  ({status})")
        if rank == 1 and meta.get("recommendation"):
            print(f"      Öneri: {meta['recommendation']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
