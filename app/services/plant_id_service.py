"""
Plant.id v3 hastalik tespit servisi.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger


PLANT_ID_API_URL = "https://api.plant.id/v3"
PLANT_ID_DETAILS = "local_name,description,treatment,classification,common_names,cause"


def _normalize_text(value: Any) -> str:
    """Metinleri tek satir, temiz bir forma cevirir."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def _collect_treatment_lines(treatment: dict[str, Any] | None) -> list[str]:
    """Tedavi alanlarindaki oneri cumlelerini oncelikli sirayla toplar."""
    if not isinstance(treatment, dict):
        return []

    ordered_keys = ("chemical", "biological", "prevention")
    collected: list[str] = []
    seen: set[str] = set()

    for key in ordered_keys:
        values = treatment.get(key) or []
        if not isinstance(values, list):
            continue
        for value in values:
            line = _normalize_text(value)
            if not line or line in seen:
                continue
            seen.add(line)
            collected.append(line)
            if len(collected) >= 3:
                return collected

    return collected


def _collect_treatment_titles(treatment: dict[str, Any] | None) -> list[str]:
    """Tedavi alanlarindaki dolu basliklari kullanici dostu etiketlere cevirir."""
    if not isinstance(treatment, dict):
        return []

    title_map = {
        "chemical": "Kimyasal",
        "biological": "Biyolojik",
        "prevention": "Onleme",
    }

    titles: list[str] = []
    for key in ("chemical", "biological", "prevention"):
        values = treatment.get(key) or []
        if isinstance(values, list) and any(_normalize_text(value) for value in values):
            titles.append(title_map[key])

    return titles


def _pick_best_suggestion(suggestions: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Gereksiz/genel kategorileri geri plana atarak en iyi tahmini secer."""
    if not suggestions:
        return None

    ordered = sorted(
        suggestions,
        key=lambda item: float(item.get("probability") or 0),
        reverse=True,
    )
    non_redundant = [item for item in ordered if not item.get("redundant")]
    return (non_redundant or ordered)[0]


def _build_recommendation(details: dict[str, Any]) -> str:
    """Aciklama ve tedavi alanlarindan kullaniciya okunakli ozet uretir."""
    description = _normalize_text(details.get("description"))
    treatment_lines = _collect_treatment_lines(details.get("treatment"))

    parts: list[str] = []
    if description:
        parts.append(description)
    if treatment_lines:
        parts.append("Oneri: " + " ".join(treatment_lines[:2]))

    return " ".join(parts) or "Net tedavi onerisi alinamadi. Fotografi farkli bir acidan tekrar deneyin."


def _build_analysis_result(response_data: dict[str, Any]) -> dict[str, Any]:
    """Plant.id yanitini mobil uygulamanin bekledigi formata map eder."""
    result = response_data.get("result") or {}
    input_data = response_data.get("input") or {}
    access_token = response_data.get("access_token") or f"plant-{int(datetime.now(timezone.utc).timestamp())}"
    timestamp = input_data.get("datetime") or datetime.now(timezone.utc).isoformat()

    is_healthy = result.get("is_healthy") or {}
    healthy_probability = float(is_healthy.get("probability") or 0)
    if bool(is_healthy.get("binary")):
        return {
            "id": access_token,
            "imageUri": "",
            "timestamp": timestamp,
            "diseaseName": "Saglikli Bitki",
            "confidence": healthy_probability,
            "recommendation": "Belirgin bir hastalik bulgusu saptanmadi. Bitkiyi izlemeye devam edin ve sulama-besleme dengesini koruyun.",
            "treatmentTitles": [],
            "status": "healthy",
        }

    suggestions = ((result.get("disease") or {}).get("suggestions") or [])
    best = _pick_best_suggestion(suggestions)
    if not best:
        return {
            "id": access_token,
            "imageUri": "",
            "timestamp": timestamp,
            "diseaseName": "Bitki Stresi",
            "confidence": max(1 - healthy_probability, 0),
            "recommendation": "Net bir hastalik bulunamadi. Yaprak, govde veya sorunlu bolgenin daha net bir fotografiyla tekrar deneyin.",
            "treatmentTitles": [],
            "status": "warning",
        }

    details = best.get("details") or {}
    treatment = details.get("treatment")
    confidence = float(best.get("probability") or max(1 - healthy_probability, 0))
    disease_name = (
        _normalize_text(details.get("local_name"))
        or _normalize_text(best.get("name"))
        or "Bitki Hastaligi"
    )

    return {
        "id": access_token,
        "imageUri": "",
        "timestamp": timestamp,
        "diseaseName": disease_name,
        "confidence": confidence,
        "recommendation": _build_recommendation(details),
        "treatmentTitles": _collect_treatment_titles(treatment),
        "status": "critical" if confidence >= 0.75 else "warning",
    }


async def _request_health_assessment(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    payload: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Once resmi health endpoint'ini, gerekirse identification fallback'ini dener."""
    response = await client.post(
        f"{PLANT_ID_API_URL}/health_assessment",
        headers=headers,
        params=params,
        json=payload,
    )
    if response.status_code not in {404, 405}:
        response.raise_for_status()
        return response.json()

    fallback_payload = {**payload, "health": "only"}
    response = await client.post(
        f"{PLANT_ID_API_URL}/identification",
        headers=headers,
        params=params,
        json=fallback_payload,
    )
    response.raise_for_status()
    return response.json()


async def analyze_plant_health(image_bytes: bytes) -> dict[str, Any]:
    """Gonderilen gorseli Plant.id uzerinden analiz eder."""
    if not settings.PLANT_ID_API_KEY:
        raise ValueError("Plant.id entegrasyonu icin .env icine PLANT_ID_API_KEY ekleyin.")

    payload = {
        "images": [base64.b64encode(image_bytes).decode("ascii")],
        "similar_images": True,
    }
    params = {
        "details": PLANT_ID_DETAILS,
        "language": "tr",
        "full_disease_list": False,
    }
    headers = {"Api-Key": settings.PLANT_ID_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response_data = await _request_health_assessment(client, headers, payload, params)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Plant.id istegi reddedildi: status={} body={}",
            exc.response.status_code,
            _normalize_text(exc.response.text)[:400],
        )
        raise RuntimeError("Plant hastalik servisi istegi reddetti. API anahtari ve kota ayarlarini kontrol edin.") from exc
    except httpx.HTTPError as exc:
        logger.warning(f"Plant.id baglanti hatasi: {exc}")
        raise RuntimeError("Plant hastalik servisine baglanilamadi.") from exc

    if "result" not in response_data:
        logger.warning(f"Plant.id beklenmeyen yanit dondu: {response_data}")
        raise RuntimeError("Plant hastalik servisi analiz sonucunu donmedi.")

    return _build_analysis_result(response_data)
