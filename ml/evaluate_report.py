"""
Test kümesi değerlendirmesi + ara rapor grafikleri.

Çıktılar (varsayılan: ml/report/):
  - confusion_test.png          — karmaşıklık matrisi
  - per_class_f1.png            — sınıf bazında F1
  - confidence_hist.png         — doğru/yanlış güven dağılımı
  - margin_hist.png             — top1-top2 marj dağılımı
  - threshold_sweep.png         — eşik vs reddetme / kabul edilen doğruluk
  - healthy_vs_disease.png      — sağlıklı vs hastalık güven karşılaştırması
  - gate_acceptance_by_class.png — mevcut API eşiğinde sınıf kabul oranı
  - evaluation_report.json      — sayısal özet

Her grafik A4 genişliğinde tek sayfa olarak üretilir (Word için okunabilir boyut).

Kullanım:
    python ml/evaluate_report.py
    python ml/evaluate_report.py --min-conf 0.50 --min-margin 0.05 --high-bypass 0.68
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from tqdm import tqdm

ML_DIR = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT = ML_DIR / "checkpoints" / "best.pt"
DEFAULT_TEST_DIR = ML_DIR / "data" / "splits" / "test"
DEFAULT_OUT = ML_DIR / "report"

# A4 dikey (inç) — Word'e tam sayfa yerleşim
A4_W, A4_H = 8.27, 11.69
WORD_DPI = 180


def build_model(num_classes: int) -> nn.Module:
    model = models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(nn.Dropout(p=0.3), nn.Linear(in_features, num_classes))
    return model


def is_confident_enough(conf: float, margin: float, min_conf: float, min_margin: float, high_bypass: float) -> bool:
    if conf < min_conf:
        return False
    if conf >= high_bypass:
        return True
    return margin >= min_margin


def short_label(class_name: str, max_len: int = 28) -> str:
    s = class_name.replace("___", " / ").replace("_", " ")
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def collect_predictions(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    class_names: List[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    model.eval()
    with torch.no_grad():
        for images, targets in tqdm(loader, desc="test"):
            images = images.to(device)
            probs = torch.softmax(model(images), dim=1)
            top2 = probs.topk(2, dim=1)
            preds = top2.indices[:, 0].cpu()
            conf = top2.values[:, 0].cpu()
            margin = (top2.values[:, 0] - top2.values[:, 1]).cpu()
            for t, p, c, m in zip(targets, preds, conf, margin):
                t_i, p_i = int(t), int(p)
                rows.append(
                    {
                        "true_idx": t_i,
                        "pred_idx": p_i,
                        "true_class": class_names[t_i],
                        "pred_class": class_names[p_i],
                        "correct": t_i == p_i,
                        "confidence": float(c),
                        "margin": float(m),
                        "is_healthy": "healthy" in class_names[t_i].lower(),
                    }
                )
    return rows


def gate_stats(rows: List[Dict[str, Any]], min_conf: float, min_margin: float, high_bypass: float) -> Dict[str, Any]:
    accepted = [
        r for r in rows if is_confident_enough(r["confidence"], r["margin"], min_conf, min_margin, high_bypass)
    ]
    rejected = len(rows) - len(accepted)
    acc_all = sum(r["correct"] for r in rows) / len(rows)
    if not accepted:
        return {
            "min_conf": min_conf,
            "min_margin": min_margin,
            "high_bypass": high_bypass,
            "accepted": 0,
            "rejected": rejected,
            "reject_rate": rejected / len(rows),
            "accepted_accuracy": None,
            "accepted_recall_correct": 0.0,
        }
    acc_acc = sum(r["correct"] for r in accepted) / len(accepted)
    correct_total = sum(r["correct"] for r in rows)
    kept_correct = sum(r["correct"] for r in accepted)
    return {
        "min_conf": min_conf,
        "min_margin": min_margin,
        "high_bypass": high_bypass,
        "accepted": len(accepted),
        "rejected": rejected,
        "reject_rate": rejected / len(rows),
        "top1_accuracy_all": acc_all,
        "accepted_accuracy": acc_acc,
        "accepted_recall_correct": kept_correct / correct_total if correct_total else 0.0,
    }


def per_class_gate(rows: List[Dict[str, Any]], min_conf: float, min_margin: float, high_bypass: float) -> Dict[str, Dict[str, float]]:
    by_true: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_true[r["true_class"]].append(r)
    out: Dict[str, Dict[str, float]] = {}
    for cls, items in sorted(by_true.items()):
        n = len(items)
        correct = sum(x["correct"] for x in items)
        accepted = sum(
            1
            for x in items
            if is_confident_enough(x["confidence"], x["margin"], min_conf, min_margin, high_bypass)
        )
        accepted_correct = sum(
            x["correct"]
            for x in items
            if is_confident_enough(x["confidence"], x["margin"], min_conf, min_margin, high_bypass)
        )
        out[cls] = {
            "n": n,
            "accuracy": correct / n if n else 0.0,
            "accept_rate": accepted / n if n else 0.0,
            "accepted_accuracy": accepted_correct / accepted if accepted else 0.0,
        }
    return out


def save_plots(
    rows: List[Dict[str, Any]],
    class_names: List[str],
    out_dir: Path,
    gate: Dict[str, Any],
    per_class: Dict[str, Dict[str, float]],
    sweep: List[Dict[str, Any]],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from sklearn.metrics import classification_report, confusion_matrix

    out_dir.mkdir(parents=True, exist_ok=True)

    targets = [r["true_idx"] for r in rows]
    preds = [r["pred_idx"] for r in rows]
    top1 = sum(r["correct"] for r in rows) / len(rows)

    def save_fig(fig, name: str) -> None:
        path = out_dir / name
        fig.savefig(path, dpi=WORD_DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"[INFO] {path.name}")

    # 1) Confusion matrix — tam A4 sayfa
    cm = confusion_matrix(targets, preds, labels=list(range(len(class_names))))
    fig, ax = plt.subplots(figsize=(A4_W, A4_H))
    im = ax.imshow(cm, cmap="Blues", aspect="auto")
    labels = [short_label(c, 20) for c in class_names]
    ax.set_xticks(range(len(class_names)))
    ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("Tahmin", fontsize=11)
    ax.set_ylabel("Gerçek", fontsize=11)
    ax.set_title(
        f"Test karmaşıklık matrisi — Top-1 doğruluk = %{top1 * 100:.1f} (8.982 görsel)",
        fontsize=12,
        pad=12,
    )
    plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    fig.tight_layout()
    save_fig(fig, "confusion_test.png")

    # 2) Per-class F1 — tam A4 sayfa
    report = classification_report(
        targets, preds, labels=list(range(len(class_names))), target_names=class_names, output_dict=True, zero_division=0
    )
    f1_scores = [(c, report[c]["f1-score"]) for c in class_names if c in report]
    f1_scores.sort(key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(A4_W, A4_H))
    names = [short_label(c, 32) for c, _ in f1_scores]
    vals = [v for _, v in f1_scores]
    colors = ["#2ca02c" if "healthy" in c.lower() else "#1f77b4" for c, _ in f1_scores]
    y = list(range(len(names)))
    ax.barh(y, vals, color=colors, height=0.72)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("F1 skoru", fontsize=11)
    ax.set_title("Sınıf bazında F1 skorları (yeşil = sağlıklı sınıflar)", fontsize=12, pad=12)
    ax.axvline(0.9, color="gray", ls="--", lw=0.9, alpha=0.6)
    ax.tick_params(axis="x", labelsize=10)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    save_fig(fig, "per_class_f1.png")

    # 3) Confidence histogram — tek sayfa
    conf_ok = [r["confidence"] for r in rows if r["correct"]]
    conf_bad = [r["confidence"] for r in rows if not r["correct"]]
    fig, ax = plt.subplots(figsize=(A4_W, A4_H * 0.62))
    bins = np.linspace(0, 1, 41)
    ax.hist(conf_ok, bins=bins, alpha=0.65, label=f"Doğru (n={len(conf_ok)})", color="#2ca02c", density=True)
    ax.hist(conf_bad, bins=bins, alpha=0.65, label=f"Yanlış (n={len(conf_bad)})", color="#d62728", density=True)
    ax.axvline(gate["min_conf"], color="black", ls="--", lw=1.2, label=f"min_conf={gate['min_conf']}")
    ax.axvline(gate["high_bypass"], color="#ff7f0e", ls=":", lw=1.2, label=f"high_bypass={gate['high_bypass']}")
    ax.set_xlabel("Softmax güven (top-1)", fontsize=11)
    ax.set_ylabel("Yoğunluk", fontsize=11)
    ax.set_title("Güven skoru dağılımı — doğru vs yanlış tahmin", fontsize=12, pad=12)
    ax.legend(fontsize=10)
    ax.tick_params(labelsize=10)
    fig.tight_layout()
    save_fig(fig, "confidence_hist.png")

    # 4) Margin histogram
    m_ok = [r["margin"] for r in rows if r["correct"]]
    m_bad = [r["margin"] for r in rows if not r["correct"]]
    fig, ax = plt.subplots(figsize=(A4_W, A4_H * 0.62))
    bins = np.linspace(0, 1, 41)
    ax.hist(m_ok, bins=bins, alpha=0.65, label="Doğru", color="#2ca02c", density=True)
    ax.hist(m_bad, bins=bins, alpha=0.65, label="Yanlış", color="#d62728", density=True)
    ax.axvline(gate["min_margin"], color="black", ls="--", lw=1.2, label=f"min_margin={gate['min_margin']}")
    ax.set_xlabel("Marj (top1 − top2)", fontsize=11)
    ax.set_ylabel("Yoğunluk", fontsize=11)
    ax.set_title("Belirsizlik marjı dağılımı", fontsize=12, pad=12)
    ax.legend(fontsize=10)
    ax.tick_params(labelsize=10)
    fig.tight_layout()
    save_fig(fig, "margin_hist.png")

    # 5) Healthy vs disease confidence — tek sayfa
    h_conf = [r["confidence"] for r in rows if r["is_healthy"]]
    d_conf = [r["confidence"] for r in rows if not r["is_healthy"]]
    fig, ax = plt.subplots(figsize=(A4_W, A4_H * 0.62))
    ax.boxplot([h_conf, d_conf], tick_labels=["Sağlıklı (gerçek)", "Hastalık (gerçek)"], widths=0.5)
    ax.axhline(gate["min_conf"], color="black", ls="--", lw=1.2, label="min_conf")
    ax.set_ylabel("Güven skoru", fontsize=11)
    ax.set_title("Sağlıklı vs hastalık — güven dağılımı (doğru etiketli örnekler)", fontsize=12, pad=12)
    ax.legend(fontsize=10)
    ax.tick_params(labelsize=10)
    fig.tight_layout()
    save_fig(fig, "healthy_vs_disease_conf.png")

    # 6) Gate acceptance by class — tam A4 sayfa
    items = sorted(per_class.items(), key=lambda x: x[1]["accept_rate"])
    fig, ax = plt.subplots(figsize=(A4_W, A4_H))
    names = [short_label(c, 32) for c, _ in items]
    rates = [v["accept_rate"] for _, v in items]
    colors = ["#2ca02c" if "healthy" in c.lower() else "#9467bd" for c, _ in items]
    gy = list(range(len(names)))
    ax.barh(gy, rates, color=colors, height=0.72)
    ax.set_yticks(gy)
    ax.set_yticklabels(names, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Kabul oranı (API eşiği geçen)", fontsize=11)
    ax.set_title(
        f"Güven eşiği sonrası sınıf bazında kabul oranı "
        f"(conf≥{gate['min_conf']}, margin≥{gate['min_margin']} veya conf≥{gate['high_bypass']})",
        fontsize=11,
        pad=12,
    )
    ax.tick_params(axis="x", labelsize=10)
    fig.tight_layout()
    save_fig(fig, "gate_acceptance_by_class.png")

    # 7) Threshold sweep — tek sayfa
    fig, ax1 = plt.subplots(figsize=(A4_W, A4_H * 0.62))
    confs = sorted({s["min_conf"] for s in sweep})
    rej = [next(s["reject_rate"] for s in sweep if s["min_conf"] == c) for c in confs]
    acc = [next(s["accepted_accuracy"] for s in sweep if s["min_conf"] == c) for c in confs]
    ax1.plot(confs, rej, "o-", color="#1f77b4", lw=2, markersize=7, label="Reddetme oranı")
    ax1.set_xlabel("min_conf (margin=0.05, bypass=0.68 sabit)", fontsize=11)
    ax1.set_ylabel("Reddetme oranı", color="#1f77b4", fontsize=11)
    ax1.tick_params(axis="y", labelcolor="#1f77b4", labelsize=10)
    ax1.tick_params(axis="x", labelsize=10)
    ax2 = ax1.twinx()
    ax2.plot(confs, acc, "s-", color="#d62728", lw=2, markersize=7, label="Kabul edilen doğruluk")
    ax2.set_ylabel("Kabul edilen doğruluk", color="#d62728", fontsize=11)
    ax2.tick_params(axis="y", labelcolor="#d62728", labelsize=10)
    ax1.set_title("Güven eşiği taraması — reddetme oranı vs kabul edilen doğruluk", fontsize=12, pad=12)
    fig.tight_layout()
    save_fig(fig, "threshold_sweep.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--test-dir", type=Path, default=DEFAULT_TEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--min-conf", type=float, default=0.50)
    parser.add_argument("--min-margin", type=float, default=0.05)
    parser.add_argument("--high-bypass", type=float, default=0.68)
    args = parser.parse_args()

    if not args.checkpoint.exists() or not args.test_dir.exists():
        print("[ERROR] checkpoint veya test klasörü yok")
        return 1

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    classes: List[str] = ckpt["classes"]
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

    rows = collect_predictions(model, loader, device, classes)
    gate = gate_stats(rows, args.min_conf, args.min_margin, args.high_bypass)
    per_class = per_class_gate(rows, args.min_conf, args.min_margin, args.high_bypass)

    healthy_rows = [r for r in rows if r["is_healthy"]]
    healthy_acc = sum(r["correct"] for r in healthy_rows) / len(healthy_rows) if healthy_rows else 0.0
    healthy_accept = sum(
        1
        for r in healthy_rows
        if is_confident_enough(r["confidence"], r["margin"], args.min_conf, args.min_margin, args.high_bypass)
    )
    healthy_accept_correct = sum(
        r["correct"]
        for r in healthy_rows
        if is_confident_enough(r["confidence"], r["margin"], args.min_conf, args.min_margin, args.high_bypass)
    )

    sweep: List[Dict[str, Any]] = []
    for mc in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
        sweep.append(gate_stats(rows, mc, args.min_margin, args.high_bypass))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    save_plots(rows, classes, args.out_dir, gate, per_class, sweep)

    healthy_detail = {
        cls: per_class[cls]
        for cls in per_class
        if "healthy" in cls.lower()
    }

    report = {
        "n_test": len(rows),
        "top1_accuracy": sum(r["correct"] for r in rows) / len(rows),
        "gate": gate,
        "healthy_summary": {
            "n": len(healthy_rows),
            "accuracy": healthy_acc,
            "accept_rate": healthy_accept / len(healthy_rows) if healthy_rows else 0.0,
            "accepted_accuracy": healthy_accept_correct / healthy_accept if healthy_accept else 0.0,
        },
        "healthy_per_class": healthy_detail,
        "threshold_sweep": sweep,
        "recommended_api_thresholds": {
            "PLANT_MIN_CONFIDENCE": args.min_conf,
            "PLANT_MIN_CONFIDENCE_MARGIN": args.min_margin,
            "PLANT_HIGH_CONFIDENCE_BYPASS": args.high_bypass,
        },
    }
    report_path = args.out_dir / "evaluation_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== Test: {len(rows)} gorsel, Top-1 = {report['top1_accuracy']:.4f} ===")
    print(f"  API esigi: conf>={args.min_conf}, margin>={args.min_margin} veya conf>={args.high_bypass}")
    print(f"  Reddetme: {gate['reject_rate']*100:.1f}%  |  Kabul edilen dogruluk: {gate['accepted_accuracy']:.4f}")
    print(f"  Saglikli siniflar: acc={healthy_acc:.4f}, kabul={healthy_accept}/{len(healthy_rows)} "
          f"({100*healthy_accept/len(healthy_rows):.1f}%)")
    print(f"\n[INFO] Grafikler: {args.out_dir}")
    print(f"[INFO] JSON: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
