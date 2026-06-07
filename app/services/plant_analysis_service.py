"""
Bitki hastalığı görüntü sınıflandırması + JSON tabanlı etken madde eşlemesi.

Model: MobileNetV2 checkpoint (train.py ile uyumlu).
Etken madde listesi: ml/treatment_active_ingredients.json (hallüsinasyon yok).
İsteğe bağlı: yerel LLM ile özet metin (sadece verilen JSON'dan türetilir).
"""

from __future__ import annotations

import io
import json
import threading
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageFile

from app.core.config import settings
from app.core.logging import logger
from app.services.bku_enrichment import compact_bku_for_llm

ImageFile.LOAD_TRUNCATED_IMAGES = True


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class PlantPrediction:
    class_key: str
    confidence: float
    margin: float  # top1 - top2 softmax olasılığı


class PlantAnalysisService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model = None
        self._device = None
        self._labels_meta: Dict[str, Any] = {}
        self._classes_ui: Dict[str, Any] = {}  # class_key -> {tr, crop, status, recommendation}
        self._treatment_by_class: Dict[str, List[Dict[str, str]]] = {}
        self._disclaimer: str = ""
        self._checkpoint_classes: Optional[List[str]] = None
        self._load_error: Optional[str] = None

    def _paths(self) -> Tuple[Path, Path, Path]:
        root = _project_root()
        ckpt = Path(settings.PLANT_CHECKPOINT_PATH or root / "ml" / "checkpoints" / "best.pt")
        labels_path = Path(settings.PLANT_LABELS_PATH or root / "ml" / "class_labels.json")
        treat_path = Path(settings.PLANT_TREATMENT_PATH or root / "ml" / "treatment_active_ingredients.json")
        return ckpt, labels_path, treat_path

    def load_static_json(self) -> None:
        """Checkpoint olmadan JSON'ları yükle (test / health için)."""
        _, labels_path, treat_path = self._paths()
        if labels_path.exists():
            data = json.loads(labels_path.read_text(encoding="utf-8"))
            self._labels_meta = data.get("_meta", {})
            self._classes_ui = data.get("classes", {})
        else:
            logger.warning(f"class_labels.json bulunamadı: {labels_path}")

        if treat_path.exists():
            tdata = json.loads(treat_path.read_text(encoding="utf-8"))
            self._disclaimer = str(tdata.get("_meta", {}).get("disclaimer_tr", ""))
            self._treatment_by_class = tdata.get("by_class", {})
        else:
            logger.warning(f"treatment_active_ingredients.json bulunamadı: {treat_path}")
            self._disclaimer = (
                "Kayıtlı bitki koruma ürününü etiket ve ziraat mühendisi kontrolünde kullanın."
            )

    def _ensure_torch_model(self) -> None:
        if self._model is not None or self._load_error:
            return
        ckpt, _, _ = self._paths()
        if not ckpt.exists():
            self._load_error = f"Checkpoint yok: {ckpt}"
            logger.warning(self._load_error)
            return
        try:
            import torch
            import torch.nn as nn
            from torchvision import models, transforms
        except ImportError as e:
            self._load_error = f"torch/torchvision yüklü değil: {e}"
            logger.error(self._load_error)
            return

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        try:
            ckpt_obj = torch.load(str(ckpt), map_location=device, weights_only=False)
            classes: List[str] = ckpt_obj["classes"]
            state = ckpt_obj["state_dict"]
            mean = ckpt_obj.get("mean", [0.485, 0.456, 0.406])
            std = ckpt_obj.get("std", [0.229, 0.224, 0.225])
            img_size = int(ckpt_obj.get("img_size", 224))

            model = models.mobilenet_v2(weights=None)
            in_features = model.classifier[1].in_features
            model.classifier = nn.Sequential(nn.Dropout(p=0.3), nn.Linear(in_features, len(classes)))
            model.load_state_dict(state)
            model.eval()
            model.to(device)

            eval_tf = transforms.Compose(
                [
                    transforms.Resize(img_size + 32),
                    transforms.CenterCrop(img_size),
                    transforms.ToTensor(),
                    transforms.Normalize(mean, std),
                ]
            )

            self._model = model
            self._device = device
            self._eval_transform = eval_tf
            self._checkpoint_classes = classes
            self._load_error = None
            logger.info(
                f"Bitki CNN yüklendi ({len(classes)} sınıf), cihaz={device}, ckpt={ckpt.name}"
            )
        except Exception as e:
            self._load_error = str(e)
            logger.exception(f"Bitki modeli yüklenemedi: {e}")

    def predict_image_bytes(self, data: bytes) -> PlantPrediction:
        """Görüntü baytlarından sınıf, güven ve top1-top2 marjı. Model yoksa hata fırlatır."""
        self._ensure_torch_model()
        if self._model is None:
            raise RuntimeError(self._load_error or "Model yüklenemedi")

        import torch

        img = Image.open(io.BytesIO(data)).convert("RGB")
        with self._lock:
            tensor = self._eval_transform(img).unsqueeze(0).to(self._device)
            with torch.no_grad():
                logits = self._model(tensor)
                probs = torch.softmax(logits, dim=1)[0]
                top2 = torch.topk(probs, k=min(2, probs.numel()))
                conf = float(top2.values[0].item())
                idx = int(top2.indices[0].item())
                second = float(top2.values[1].item()) if top2.values.numel() > 1 else 0.0
                class_key = self._checkpoint_classes[idx]
                return PlantPrediction(
                    class_key=class_key,
                    confidence=conf,
                    margin=conf - second,
                )

    def is_confident_enough(self, prediction: PlantPrediction) -> bool:
        """Eşik altı veya belirsiz (düşük marj) tahminleri reddet."""
        return (
            prediction.confidence >= settings.PLANT_MIN_CONFIDENCE
            and prediction.margin >= settings.PLANT_MIN_CONFIDENCE_MARGIN
        )

    def build_rejection_payload(self, prediction: PlantPrediction) -> Dict[str, Any]:
        """Düşük güven / belirsiz görüntü — tanı ve tedavi önerisi sunulmaz."""
        disc = self._disclaimer or (
            "Kayıtlı bitki koruma ürününü etiket ve ziraat mühendisi kontrolünde kullanın."
        )
        return {
            "detected": False,
            "diseaseName": "Bitki tespit edilemedi",
            "classKey": "",
            "crop": "",
            "confidence": round(prediction.confidence, 4),
            "confidenceMargin": round(prediction.margin, 4),
            "minConfidenceRequired": settings.PLANT_MIN_CONFIDENCE,
            "minMarginRequired": settings.PLANT_MIN_CONFIDENCE_MARGIN,
            "status": "unknown",
            "recommendation": (
                "Görüntü güvenle sınıflandırılamadı. Tek bir yaprağı yakın plan, net odak "
                "ve iyi ışıkta çekip tekrar deneyin. Arka plan mümkün olduğunca sade olsun; "
                "yaprak dışı (meyve, toprak, el) fotoğraflarından kaçının."
            ),
            "activeIngredients": [],
            "disclaimer": disc,
            "narrativeSummary": None,
            "modelLoaded": self._model is not None,
        }

    def build_payload(
        self,
        prediction: PlantPrediction,
    ) -> Dict[str, Any]:
        """Model çıktısı + JSON birleştirme (LLM hariç)."""
        if not self.is_confident_enough(prediction):
            return self.build_rejection_payload(prediction)

        class_key = prediction.class_key
        confidence = prediction.confidence
        ui = self._classes_ui.get(class_key, {})
        tr_name = ui.get("tr") or class_key
        crop = ui.get("crop") or ""
        status = ui.get("status") or "warning"
        recommendation = ui.get("recommendation") or "Konu için ziraat uzmanına danışın."

        raw_ing = self._treatment_by_class.get(class_key, [])
        ingredients = [{"name": x["name"], "role": x.get("role", ""), "notes": x.get("notes", "")} for x in raw_ing]

        disc = self._disclaimer or (
            "Kayıtlı bitki koruma ürününü etiket ve ziraat mühendisi kontrolünde kullanın."
        )

        return {
            "detected": True,
            "diseaseName": tr_name,
            "classKey": class_key,
            "crop": crop,
            "confidence": round(confidence, 4),
            "confidenceMargin": round(prediction.margin, 4),
            "status": status,
            "recommendation": recommendation,
            "activeIngredients": ingredients,
            "disclaimer": disc,
            "narrativeSummary": None,
            "modelLoaded": self._model is not None,
        }

    def enrich_with_llm(self, payload: Dict[str, Any]) -> Optional[str]:
        """Yerel Llama ile kısa özet — yalnızca payload içeriğine dayanır."""
        from app.services.llm_service import llm_service

        if not llm_service.model_loaded or not llm_service.llm:
            logger.warning("LLM yüklü değil; narrative_summary atlanıyor")
            return None

        # Prompt: sızdırma yok, uydurma yok
        import json as _json

        compact = {
            "tanı": payload.get("diseaseName"),
            "bitki": payload.get("crop"),
            "durum": payload.get("status"),
            "öneri": payload.get("recommendation"),
            "etken_maddeler": payload.get("activeIngredients", []),
            "uyarı": payload.get("disclaimer"),
        }
        bku_slim = compact_bku_for_llm(payload.get("bkuMrlEnrichment"))
        if bku_slim:
            compact["bkü_mrl_ornek"] = bku_slim
        prompt = f"""<|im_start|>system
Sen Türkiye'de çiftçilere yardımcı olan bir ziraat asistanısın.
Aşağıdaki JSON YAPISI bilgisayar çıktısıdır; içinde OLMAYAN etken madde veya ürün adı UYDURMA.
Sadece verilen metinleri kullanarak 4-6 kısa paragrafta Türkçe özet yaz (Markdown başlık kullanabilirsin).
Son paragrafta mutlaka etiket + kayıtlı ürün + ziraat mühendisi uyarısını tekrarla.
<|im_end|>
<|im_start|>user
/no_think
JSON:
{_json.dumps(compact, ensure_ascii=False)}
<|im_end|>
<|im_start|>assistant
"""
        try:
            text = llm_service.generate(prompt, max_tokens=512)
            return text.strip() or None
        except Exception as e:
            logger.error(f"LLM özet hatası: {e}")
            return None

    @property
    def json_bundle_loaded(self) -> bool:
        return len(self._classes_ui) > 0

    @property
    def cnn_loaded(self) -> bool:
        return self._model is not None

    @property
    def model_available(self) -> bool:
        self._ensure_torch_model()
        return self._model is not None

    @property
    def last_load_error(self) -> Optional[str]:
        return self._load_error


plant_analysis_service = PlantAnalysisService()
