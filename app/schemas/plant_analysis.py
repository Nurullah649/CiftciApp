"""Bitki görüntü analizi API yanıt şemaları."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ActiveIngredientItem(BaseModel):
    """JSON eşlemesinden gelen etken madde satırı — yeni isim uydurulmaz."""

    name: str = Field(..., description="Etken madde veya müdahale başlığı")
    role: str = Field("", description="Kısa rol (örn. koruyucu fungisit)")
    notes: str = Field("", description="Güvenlik / kullanım notu")


class PlantAnalysisResponse(BaseModel):
    """Mobil ve web için analyze-plant çıktısı."""

    disease_name: str = Field(..., serialization_alias="diseaseName")
    class_key: str = Field(..., serialization_alias="classKey")
    crop: str = ""
    confidence: float = Field(..., ge=0.0, le=1.0)
    status: Literal["healthy", "warning", "critical"]
    recommendation: str = Field(
        ...,
        description="Kültürel / genel mücadele önerisi (class_labels.json)",
    )
    active_ingredients: List[ActiveIngredientItem] = Field(
        default_factory=list,
        serialization_alias="activeIngredients",
    )
    disclaimer: str = Field(
        ...,
        description="Yasal/genel uyarı metni",
    )
    narrative_summary: Optional[str] = Field(
        None,
        serialization_alias="narrativeSummary",
        description="İsteğe bağlı LLM ile düzgün dil özet",
    )
    model_loaded: bool = Field(True, serialization_alias="modelLoaded")

    bku_mrl_enrichment: Optional[Dict[str, Any]] = Field(
        None,
        serialization_alias="bkuMrlEnrichment",
        description="İsteğe bağlı BKÜ MRL tablosu özeti (canlı çekim)",
    )

    model_config = {"populate_by_name": True}
