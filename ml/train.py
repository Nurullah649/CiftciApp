"""
MobileNetV2 transfer learning eğitim scripti.

Aşamalar:
    1) Önce sadece sınıflandırma başlığını eğit (backbone donuk) → "warm-up"
    2) Sonra son blokları açıp düşük LR ile fine-tune et → "fine-tune"

Çıktılar (varsayılan ml/checkpoints/):
    - best.pt           : En iyi val acc (state_dict + class_to_idx + metadata)
    - last.pt           : Son epoch
    - history.json      : Epoch başına loss/acc
    - confusion_val.png : Validation confusion matrix (matplotlib varsa)

Kullanım:
    python ml/train.py
    python ml/train.py --epochs-head 5 --epochs-finetune 10 --batch-size 64
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageFile
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, models, transforms
from tqdm import tqdm

ML_DIR = Path(__file__).resolve().parent
DEFAULT_SPLIT_DIR = ML_DIR / "data" / "splits"
DEFAULT_CHECKPOINT_DIR = ML_DIR / "checkpoints"

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
IMG_SIZE = 224

# Bazı PlantDoc görselleri progressive JPEG / truncated olabiliyor — PIL'in default davranışı
# bunlarda IOError fırlatır. Eğitim ortasında crash yerine kısmen yüklenmiş veriyi kabul et.
ImageFile.LOAD_TRUNCATED_IMAGES = True


def rgb_loader(path: str) -> Image.Image:
    """ImageFolder için özel loader: TÜM görselleri RGB'ye çevirir.

    PlantVillage 256x256 RGB; PlantDoc içinde 5 CMYK + 5 RGBA + 1 L mevcut.
    Default loader bunları olduğu gibi döner → ToTensor() 1-kanal/4-kanal
    tensor üretir → MobileNetV2 3-kanal input bekler → CRASH.

    Bu loader convert("RGB") ile her görseli garantili 3-kanal yapar.
    """
    with open(path, "rb") as f:
        with Image.open(f) as img:
            return img.convert("RGB")


def build_dataloaders(
    split_dir: Path,
    batch_size: int,
    num_workers: int,
    sampling: str = "shuffle",
) -> Tuple[DataLoader, DataLoader, List[str], List[int]]:
    """sampling:
        - 'shuffle'   : standart uniform shuffle (varsayılan)
        - 'weighted'  : WeightedRandomSampler — az örnekli sınıfı daha sık görür
                        (CrossEntropyLoss(weight=...) kullanmazsan bunu seç)
    Dönüş:  train_loader, val_loader, classes, train_targets (class_weight hesabı için)
    """
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.RandomRotation(20),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize(IMG_SIZE + 32),
        transforms.CenterCrop(IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])

    train_ds = datasets.ImageFolder(split_dir / "train", transform=train_tf, loader=rgb_loader)
    val_ds = datasets.ImageFolder(split_dir / "val", transform=eval_tf, loader=rgb_loader)
    assert train_ds.classes == val_ds.classes, "train/val class listesi eşleşmiyor"

    train_targets = [t for _, t in train_ds.samples]

    sampler = None
    shuffle = True
    if sampling == "weighted":
        counts = Counter(train_targets)
        per_class_weight = {c: 1.0 / counts[c] for c in counts}
        sample_weights = [per_class_weight[t] for t in train_targets]
        sampler = WeightedRandomSampler(
            weights=sample_weights, num_samples=len(sample_weights), replacement=True,
        )
        shuffle = False

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        sampler=sampler,
        shuffle=shuffle and sampler is None,
        num_workers=num_workers,
        pin_memory=True,
        persistent_workers=num_workers > 0,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
        persistent_workers=num_workers > 0,
    )
    return train_loader, val_loader, train_ds.classes, train_targets


def compute_class_weights(
    targets: List[int], num_classes: int, scheme: str,
) -> Optional[torch.Tensor]:
    """Dengesiz sınıflar için CrossEntropyLoss ağırlığı.

    scheme:
        - 'none'     : None (ağırlık yok)
        - 'inverse'  : w_c = N / (K * n_c)   — sklearn 'balanced'
        - 'sqrt'     : w_c = sqrt(N / n_c)   — daha yumuşak, çok dengesiz sınıflarda iyi
        - 'effective': Cui et al. 2019, "Class-Balanced Loss Based on Effective Number"
    """
    if scheme == "none":
        return None

    counts = Counter(targets)
    n_total = sum(counts.values())
    weights = []
    for c in range(num_classes):
        n_c = counts.get(c, 1)
        if scheme == "inverse":
            w = n_total / (num_classes * n_c)
        elif scheme == "sqrt":
            w = math.sqrt(n_total / n_c)
        elif scheme == "effective":
            beta = 0.9999
            eff_num = (1.0 - beta ** n_c) / (1.0 - beta)
            w = 1.0 / eff_num
        else:
            raise ValueError(f"Bilinmeyen scheme: {scheme}")
        weights.append(w)

    w_arr = torch.tensor(weights, dtype=torch.float32)
    w_arr = w_arr / w_arr.mean()
    return w_arr


class FocalLoss(nn.Module):
    """Focal Loss (Lin et al. 2017, "Focal Loss for Dense Object Detection").

        FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)

    Etki: doğru bilinen kolay örnekleri loss'ta düşürür, model zor örneklere odaklanır.
    Sınıf dengesizliğinde, az örnekli sınıfın "zor" örneklerine ekstra ağırlık vermesi
    nedeniyle CrossEntropy'den daha iyi olabilir.

    Args:
        gamma:        Odak parametresi. 0 = standart CE; 1-2 önerilen; >5 aşırı.
        alpha:        Sınıf ağırlıkları tensoru (shape: [num_classes]) veya None.
                      compute_class_weights() çıktısı kullanılabilir.
        label_smoothing: 0..1 arası — true sınıfın hedef olasılığını yumuşatır.
        reduction:    'mean' (varsayılan) | 'sum' | 'none'
    """

    def __init__(
        self,
        gamma: float = 2.0,
        alpha: Optional[torch.Tensor] = None,
        label_smoothing: float = 0.0,
        reduction: str = "mean",
    ) -> None:
        super().__init__()
        self.gamma = float(gamma)
        self.register_buffer(
            "alpha",
            alpha if alpha is not None else torch.tensor(0.0),
            persistent=False,
        )
        self.has_alpha = alpha is not None
        self.label_smoothing = float(label_smoothing)
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # targets: long [B] (sınıf indeksleri) VEYA float [B, C] (yumuşak/karışık etiketler — mixup)
        log_p = F.log_softmax(logits, dim=-1)
        with torch.no_grad():
            if targets.dim() == 1:
                n_classes = logits.size(-1)
                soft_targets = torch.zeros_like(logits)
                soft_targets.scatter_(1, targets.unsqueeze(1), 1.0)
                if self.label_smoothing > 0:
                    soft_targets = soft_targets * (1.0 - self.label_smoothing) \
                                   + self.label_smoothing / n_classes
            else:
                soft_targets = targets

        p = log_p.exp()
        focal_weight = (1.0 - p).clamp(min=1e-8) ** self.gamma
        loss_terms = -focal_weight * log_p * soft_targets

        if self.has_alpha:
            alpha = self.alpha.to(logits.device)
            loss_terms = loss_terms * alpha.unsqueeze(0)

        loss = loss_terms.sum(dim=-1)
        if self.reduction == "mean":
            return loss.mean()
        if self.reduction == "sum":
            return loss.sum()
        return loss


class SoftTargetCrossEntropy(nn.Module):
    """mixup/cutmix sonrası soft target için CrossEntropy.

    Standart nn.CrossEntropyLoss bir-hot integer hedef bekler; mixup sonrası
    hedef [B, C] olur (örn. lam * y_a + (1-lam) * y_b).
    """

    def __init__(self, weight: Optional[torch.Tensor] = None, label_smoothing: float = 0.0):
        super().__init__()
        self.weight = weight
        self.label_smoothing = float(label_smoothing)

    def forward(self, logits: torch.Tensor, soft_targets: torch.Tensor) -> torch.Tensor:
        if self.label_smoothing > 0:
            n_classes = logits.size(-1)
            soft_targets = soft_targets * (1.0 - self.label_smoothing) \
                           + self.label_smoothing / n_classes
        log_p = F.log_softmax(logits, dim=-1)
        if self.weight is not None:
            log_p = log_p * self.weight.to(logits.device).unsqueeze(0)
        return -(soft_targets * log_p).sum(dim=-1).mean()


def mixup_data(
    images: torch.Tensor,
    targets: torch.Tensor,
    alpha: float,
    num_classes: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """mixup (Zhang et al. 2017): iki örneği piksel düzeyinde karıştır.

        x' = lam * x_a + (1 - lam) * x_b
        y' = lam * one_hot(y_a) + (1 - lam) * one_hot(y_b)
        lam ~ Beta(alpha, alpha)
    """
    if alpha <= 0:
        soft = F.one_hot(targets, num_classes).float()
        return images, soft

    lam = float(np.random.beta(alpha, alpha))
    lam = max(lam, 1.0 - lam)  # her zaman çoğunluk a'da kalsın

    idx = torch.randperm(images.size(0), device=images.device)
    mixed = lam * images + (1.0 - lam) * images[idx]
    y_a = F.one_hot(targets, num_classes).float()
    y_b = F.one_hot(targets[idx], num_classes).float()
    soft = lam * y_a + (1.0 - lam) * y_b
    return mixed, soft


def cutmix_data(
    images: torch.Tensor,
    targets: torch.Tensor,
    alpha: float,
    num_classes: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """cutmix (Yun et al. 2019): bir görselden patch kesip diğerine yapıştır.

    Hedef: lam = 1 - patch_area / image_area, soft = lam*y_a + (1-lam)*y_b.
    """
    if alpha <= 0:
        soft = F.one_hot(targets, num_classes).float()
        return images, soft

    lam = float(np.random.beta(alpha, alpha))
    n, _, h, w = images.shape
    idx = torch.randperm(n, device=images.device)

    cut_ratio = math.sqrt(1.0 - lam)
    cut_w = int(w * cut_ratio)
    cut_h = int(h * cut_ratio)
    cx, cy = np.random.randint(w), np.random.randint(h)
    x1 = max(0, cx - cut_w // 2)
    y1 = max(0, cy - cut_h // 2)
    x2 = min(w, cx + cut_w // 2)
    y2 = min(h, cy + cut_h // 2)

    images = images.clone()
    images[:, :, y1:y2, x1:x2] = images[idx, :, y1:y2, x1:x2]
    lam = 1.0 - ((x2 - x1) * (y2 - y1) / (w * h))

    y_a = F.one_hot(targets, num_classes).float()
    y_b = F.one_hot(targets[idx], num_classes).float()
    soft = lam * y_a + (1.0 - lam) * y_b
    return images, soft


def maybe_mix_batch(
    images: torch.Tensor,
    targets: torch.Tensor,
    num_classes: int,
    mixup_alpha: float,
    cutmix_alpha: float,
    mix_prob: float,
) -> Tuple[torch.Tensor, torch.Tensor, bool]:
    """%mix_prob ihtimalle mixup VEYA cutmix uygula (50/50).

    Returns:
        (mixed_images, soft_targets_or_hard, was_mixed)
        was_mixed True ise soft target; False ise hard int.
    """
    if mixup_alpha <= 0 and cutmix_alpha <= 0:
        return images, targets, False
    if random.random() > mix_prob:
        return images, targets, False

    if mixup_alpha > 0 and cutmix_alpha > 0:
        use_mixup = random.random() < 0.5
    else:
        use_mixup = mixup_alpha > 0

    if use_mixup:
        mixed_img, soft = mixup_data(images, targets, mixup_alpha, num_classes)
    else:
        mixed_img, soft = cutmix_data(images, targets, cutmix_alpha, num_classes)
    return mixed_img, soft, True


def build_model(num_classes: int) -> nn.Module:
    weights = models.MobileNet_V2_Weights.IMAGENET1K_V2
    model = models.mobilenet_v2(weights=weights)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, num_classes),
    )
    return model


def set_backbone_trainable(model: nn.Module, trainable: bool, unfreeze_last_blocks: int = 0) -> None:
    """trainable=False: backbone donuk. Eğer trainable=True ve unfreeze_last_blocks>0 ise
    sadece son K blok eğitilir (rest donuk kalır)."""
    for param in model.features.parameters():
        param.requires_grad = trainable
    if trainable and unfreeze_last_blocks > 0:
        total_blocks = len(model.features)
        cutoff = total_blocks - unfreeze_last_blocks
        for i, block in enumerate(model.features):
            for p in block.parameters():
                p.requires_grad = i >= cutoff


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: torch.device, criterion: nn.Module) -> Tuple[float, float, List[int], List[int]]:
    model.eval()
    total, correct, loss_sum = 0, 0, 0.0
    all_preds: List[int] = []
    all_targets: List[int] = []
    for images, targets in loader:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        outputs = model(images)
        loss = criterion(outputs, targets)
        loss_sum += loss.item() * images.size(0)
        preds = outputs.argmax(dim=1)
        correct += (preds == targets).sum().item()
        total += images.size(0)
        all_preds.extend(preds.cpu().tolist())
        all_targets.extend(targets.cpu().tolist())
    return loss_sum / total, correct / total, all_preds, all_targets


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    criterion_soft: Optional[nn.Module],
    scaler,
    num_classes: int,
    mixup_alpha: float = 0.0,
    cutmix_alpha: float = 0.0,
    mix_prob: float = 0.5,
) -> Tuple[float, float]:
    """criterion: hard label (int) için (CE veya FocalLoss).
    criterion_soft: mixup/cutmix sonrası soft target için (SoftTargetCE veya FocalLoss).
    mixup_alpha/cutmix_alpha = 0 ise mix yapılmaz (klasik training)."""
    model.train()
    total, correct, loss_sum = 0, 0, 0.0
    pbar = tqdm(loader, desc="train", leave=False)
    for images, targets in pbar:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        mixed_images, target_used, was_mixed = maybe_mix_batch(
            images, targets, num_classes, mixup_alpha, cutmix_alpha, mix_prob,
        )

        optimizer.zero_grad(set_to_none=True)
        if scaler is not None:
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                outputs = model(mixed_images)
                if was_mixed:
                    loss = criterion_soft(outputs, target_used) if criterion_soft is not None else criterion(outputs, target_used)
                else:
                    loss = criterion(outputs, target_used)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(mixed_images)
            if was_mixed:
                loss = criterion_soft(outputs, target_used) if criterion_soft is not None else criterion(outputs, target_used)
            else:
                loss = criterion(outputs, target_used)
            loss.backward()
            optimizer.step()

        loss_sum += loss.item() * images.size(0)
        preds = outputs.argmax(dim=1)
        correct += (preds == targets).sum().item()
        total += images.size(0)
        pbar.set_postfix(loss=f"{loss.item():.3f}", acc=f"{correct/total:.3f}")
    return loss_sum / total, correct / total


def save_checkpoint(path: Path, model: nn.Module, classes: List[str], extra: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "state_dict": model.state_dict(),
        "classes": classes,
        "class_to_idx": {c: i for i, c in enumerate(classes)},
        "model_arch": "mobilenet_v2",
        "img_size": IMG_SIZE,
        "mean": IMAGENET_MEAN,
        "std": IMAGENET_STD,
        **extra,
    }
    torch.save(payload, path)


def try_save_confusion(targets: List[int], preds: List[int], classes: List[str], out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import confusion_matrix
        cm = confusion_matrix(targets, preds, labels=list(range(len(classes))))
        fig, ax = plt.subplots(figsize=(14, 12))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(len(classes)))
        ax.set_yticks(range(len(classes)))
        ax.set_xticklabels(classes, rotation=90, fontsize=6)
        ax.set_yticklabels(classes, fontsize=6)
        ax.set_xlabel("Pred")
        ax.set_ylabel("True")
        ax.set_title("Validation Confusion Matrix")
        plt.colorbar(im, ax=ax)
        fig.tight_layout()
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        print(f"[INFO] Confusion matrix kaydedildi: {out_path}")
    except Exception as e:
        print(f"[WARN] Confusion matrix oluşturulamadı: {e}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split-dir", type=Path, default=DEFAULT_SPLIT_DIR)
    parser.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    parser.add_argument("--epochs-head", type=int, default=3, help="Sadece classifier'ı eğitme epoch sayısı")
    parser.add_argument("--epochs-finetune", type=int, default=7, help="Son blokları da açarak fine-tune epoch sayısı")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr-head", type=float, default=1e-3)
    parser.add_argument("--lr-finetune", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--unfreeze-last-blocks", type=int, default=4,
                        help="Fine-tune fazında MobileNetV2'nin son kaç bloğu açılsın")
    parser.add_argument("--label-smoothing", type=float, default=0.1)
    parser.add_argument("--no-amp", action="store_true", help="Mixed precision'ı kapat")
    parser.add_argument("--class-weights", choices=["none", "inverse", "sqrt", "effective"],
                        default="sqrt",
                        help="Dengesiz sınıflar için loss ağırlığı şeması. "
                             "Hibrit dataset'te min/max oranı 36x olduğundan 'sqrt' önerilir.")
    parser.add_argument("--sampling", choices=["shuffle", "weighted"], default="shuffle",
                        help="DataLoader stratejisi. 'weighted': az örnekli sınıfı daha sık örnekler "
                             "(class_weights ile birlikte kullanma — biri yeter).")
    parser.add_argument("--loss", choices=["ce", "focal"], default="ce",
                        help="ce: CrossEntropyLoss (klasik). "
                             "focal: FocalLoss(gamma=focal_gamma) — zor örneklere odaklanır, "
                             "dengesiz dataset'te %1-2 daha iyi sonuç verebilir.")
    parser.add_argument("--focal-gamma", type=float, default=2.0,
                        help="Focal loss odak parametresi. Tipik 1.0-3.0; 2.0 önerilen.")
    parser.add_argument("--mixup-alpha", type=float, default=0.0,
                        help="mixup Beta(alpha, alpha). 0.0 = kapalı; tipik 0.2-1.0. "
                             "İki görsel pikselde karıştırılır, soft label.")
    parser.add_argument("--cutmix-alpha", type=float, default=0.0,
                        help="cutmix Beta(alpha, alpha). 0.0 = kapalı; tipik 1.0. "
                             "Bir görselden patch kesip diğerine yapıştırır.")
    parser.add_argument("--mix-prob", type=float, default=0.5,
                        help="mixup VEYA cutmix uygulama ihtimali (batch başına). 0.0-1.0 arası.")
    args = parser.parse_args()

    if not args.split_dir.exists() or not (args.split_dir / "train").exists():
        print(f"[ERROR] Split klasörü bulunamadı: {args.split_dir}")
        print("        Önce: python ml/prepare_dataset.py")
        return 1

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Cihaz: {device}")
    if device.type == "cuda":
        print(f"[INFO] GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("[WARN] GPU bulunamadı, eğitim CPU'da çok yavaş olur.")

    if args.class_weights != "none" and args.sampling == "weighted":
        print("[WARN] Hem --class-weights hem --sampling weighted aktif. "
              "Genelde biri yeterli; ikisi birden agresif kayabilir.")

    train_loader, val_loader, classes, train_targets = build_dataloaders(
        args.split_dir, args.batch_size, args.num_workers, sampling=args.sampling,
    )
    print(f"[INFO] Sınıf sayısı: {len(classes)} | train batch: {len(train_loader)} | val batch: {len(val_loader)}")

    class_weights_tensor = compute_class_weights(train_targets, len(classes), args.class_weights)
    if class_weights_tensor is not None:
        print(f"[INFO] class_weights ({args.class_weights}): "
              f"min={class_weights_tensor.min().item():.3f}  "
              f"max={class_weights_tensor.max().item():.3f}  "
              f"mean={class_weights_tensor.mean().item():.3f}")
        cw_min_idx = int(class_weights_tensor.argmin())
        cw_max_idx = int(class_weights_tensor.argmax())
        print(f"        En düşük ağırlık: {classes[cw_min_idx]}  ({class_weights_tensor[cw_min_idx]:.3f})")
        print(f"        En yüksek ağırlık: {classes[cw_max_idx]}  ({class_weights_tensor[cw_max_idx]:.3f})")
        class_weights_tensor = class_weights_tensor.to(device)

    model = build_model(num_classes=len(classes)).to(device)

    if args.loss == "focal":
        criterion = FocalLoss(
            gamma=args.focal_gamma,
            alpha=class_weights_tensor,
            label_smoothing=args.label_smoothing,
        ).to(device)
        criterion_soft = FocalLoss(
            gamma=args.focal_gamma,
            alpha=class_weights_tensor,
            label_smoothing=0.0,
        ).to(device)
        print(f"[INFO] Loss: FocalLoss(gamma={args.focal_gamma}, "
              f"alpha={'class_weights' if class_weights_tensor is not None else 'None'})")
    else:
        criterion = nn.CrossEntropyLoss(
            label_smoothing=args.label_smoothing,
            weight=class_weights_tensor,
        ).to(device)
        criterion_soft = SoftTargetCrossEntropy(
            weight=class_weights_tensor,
            label_smoothing=0.0,
        ).to(device)
        print(f"[INFO] Loss: CrossEntropyLoss(label_smoothing={args.label_smoothing}, "
              f"weight={'class_weights' if class_weights_tensor is not None else 'None'})")

    use_mix = args.mixup_alpha > 0 or args.cutmix_alpha > 0
    if use_mix:
        print(f"[INFO] Augmentation: mixup_alpha={args.mixup_alpha}  "
              f"cutmix_alpha={args.cutmix_alpha}  prob={args.mix_prob}")

    # Val/test için ayrı, label_smoothing'siz CE — val_loss'u doğru raporlamak için.
    # Focal kullanıldığında bile val metriklerinde standart CE kullanmak literatür normu
    # (Focal sadece training loss optimizasyonunda anlam taşır).
    val_criterion = nn.CrossEntropyLoss(weight=class_weights_tensor).to(device)

    scaler = torch.amp.GradScaler("cuda") if (device.type == "cuda" and not args.no_amp) else None

    history: List[Dict] = []
    best_val_acc = 0.0
    best_path = args.checkpoint_dir / "best.pt"
    last_path = args.checkpoint_dir / "last.pt"

    # =====  AŞAMA 1: Sadece classifier başlığı  =====
    set_backbone_trainable(model, trainable=False)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=args.lr_head,
        weight_decay=args.weight_decay,
    )
    print(f"\n========= AŞAMA 1: Head training ({args.epochs_head} epoch, lr={args.lr_head}) =========")

    for epoch in range(1, args.epochs_head + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(
            model, train_loader, device, optimizer, criterion, criterion_soft, scaler,
            num_classes=len(classes),
            mixup_alpha=args.mixup_alpha,
            cutmix_alpha=args.cutmix_alpha,
            mix_prob=args.mix_prob,
        )
        val_loss, val_acc, _, _ = evaluate(model, val_loader, device, val_criterion)
        dt = time.time() - t0
        print(f"[head {epoch}/{args.epochs_head}] "
              f"train_loss={tr_loss:.4f} acc={tr_acc:.4f} | "
              f"val_loss={val_loss:.4f} acc={val_acc:.4f} | {dt:.1f}s")

        history.append({"phase": "head", "epoch": epoch,
                        "train_loss": tr_loss, "train_acc": tr_acc,
                        "val_loss": val_loss, "val_acc": val_acc})
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            save_checkpoint(best_path, model, classes,
                            {"phase": "head", "epoch": epoch, "val_acc": val_acc})
            print(f"  [SAVE] best.pt  (val_acc={val_acc:.4f})")

    # =====  AŞAMA 2: Son blokları da aç, fine-tune  =====
    set_backbone_trainable(model, trainable=True, unfreeze_last_blocks=args.unfreeze_last_blocks)
    classifier_params = list(model.classifier.parameters())
    backbone_params = [p for p in model.features.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(
        [
            {"params": backbone_params, "lr": args.lr_finetune},
            {"params": classifier_params, "lr": args.lr_finetune * 2},
        ],
        weight_decay=args.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(1, args.epochs_finetune),
    )

    print(f"\n========= AŞAMA 2: Fine-tune ({args.epochs_finetune} epoch, "
          f"last_{args.unfreeze_last_blocks}_blocks, lr={args.lr_finetune}) =========")

    last_preds: List[int] = []
    last_targets: List[int] = []
    for epoch in range(1, args.epochs_finetune + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(
            model, train_loader, device, optimizer, criterion, criterion_soft, scaler,
            num_classes=len(classes),
            mixup_alpha=args.mixup_alpha,
            cutmix_alpha=args.cutmix_alpha,
            mix_prob=args.mix_prob,
        )
        val_loss, val_acc, val_preds, val_targets = evaluate(model, val_loader, device, val_criterion)
        scheduler.step()
        dt = time.time() - t0
        print(f"[ft {epoch}/{args.epochs_finetune}] "
              f"train_loss={tr_loss:.4f} acc={tr_acc:.4f} | "
              f"val_loss={val_loss:.4f} acc={val_acc:.4f} | "
              f"lr={optimizer.param_groups[0]['lr']:.2e} | {dt:.1f}s")

        history.append({"phase": "finetune", "epoch": epoch,
                        "train_loss": tr_loss, "train_acc": tr_acc,
                        "val_loss": val_loss, "val_acc": val_acc,
                        "lr": optimizer.param_groups[0]["lr"]})
        last_preds, last_targets = val_preds, val_targets

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            save_checkpoint(best_path, model, classes,
                            {"phase": "finetune", "epoch": epoch, "val_acc": val_acc})
            print(f"  [SAVE] best.pt  (val_acc={val_acc:.4f})")

    save_checkpoint(last_path, model, classes, {"phase": "finetune-last", "val_acc": best_val_acc})

    history_path = args.checkpoint_dir / "history.json"
    history_payload = {
        "config": {
            "epochs_head": args.epochs_head,
            "epochs_finetune": args.epochs_finetune,
            "batch_size": args.batch_size,
            "lr_head": args.lr_head,
            "lr_finetune": args.lr_finetune,
            "weight_decay": args.weight_decay,
            "unfreeze_last_blocks": args.unfreeze_last_blocks,
            "label_smoothing": args.label_smoothing,
            "class_weights_scheme": args.class_weights,
            "sampling": args.sampling,
            "loss": args.loss,
            "focal_gamma": args.focal_gamma if args.loss == "focal" else None,
            "mixup_alpha": args.mixup_alpha,
            "cutmix_alpha": args.cutmix_alpha,
            "mix_prob": args.mix_prob,
            "amp": scaler is not None,
        },
        "classes": classes,
        "class_weights": (class_weights_tensor.cpu().tolist()
                          if class_weights_tensor is not None else None),
        "best_val_acc": best_val_acc,
        "history": history,
    }
    history_path.write_text(json.dumps(history_payload, indent=2), encoding="utf-8")
    print(f"\n[INFO] History: {history_path}")

    if last_preds:
        try_save_confusion(last_targets, last_preds, classes,
                           args.checkpoint_dir / "confusion_val.png")

    print(f"\n[DONE] En iyi val_acc: {best_val_acc:.4f}")
    print(f"       Checkpoint: {best_path}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:128")
    raise SystemExit(main())
