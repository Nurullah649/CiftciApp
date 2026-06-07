"""
Tools Router: Genel araçlar (health, hava, harita, bitki analizi).
"""

import asyncio

import folium
from folium.plugins import MiniMap
from geopy.geocoders import Nominatim

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from app.core.security import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.services.llm_service import llm_service
from app.services.plant_analysis_service import plant_analysis_service
from app.services.bku_catalog import BKU_AUTOCOMPLETE_ENDPOINTS
from app.services.bku_enrichment import attach_bku_mrl, map_token_count
from app.services.bku_faq_fanout import DEFAULT_FANOUT_SLUGS
from app.services.rag_service import rag_service
from app.services.weather_service import (
    fetch_weather_and_location,
    get_random_urfa_location,
)
from app.utils.image_upload import prepare_plant_image_bytes
from app.schemas.chat import MapRequest

router = APIRouter(tags=["Tools"])


@router.get("/health")
async def health_check():
    """Sunucu sağlık kontrolü."""
    from app.core.database import engine

    db_ok = False
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: None)
            db_ok = True
    except Exception:
        pass

    return {
        "status": "ok",
        "model_loaded": llm_service.model_loaded,
        "plant_json_ready": plant_analysis_service.json_bundle_loaded,
        "plant_cnn_loaded": plant_analysis_service.cnn_loaded,
        "plant_cnn_error": plant_analysis_service.last_load_error,
        "bku_mrl_map_tokens": map_token_count(),
        "bku_autocomplete_catalog_entries": len(BKU_AUTOCOMPLETE_ENDPOINTS),
        "bku_faq_fanout_default_slugs": len(DEFAULT_FANOUT_SLUGS),
        "qdrant_connected": rag_service.connected,
        "database_connected": db_ok,
        "ram_usage_mb": round(llm_service.get_ram_usage(), 2),
    }


@router.post("/tools/analyze-plant")
async def analyze_plant(
    file: UploadFile = File(...),
    enrich_llm: bool = False,
    enrich_bku: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """
    Yaprak fotoğrafından hastalık tahmini (MobileNetV2) + JSON etken madde eşlemesi.
    ``enrich_llm=true`` ise yerel LLM ile kısa Türkçe özet (yalnızca JSON içeriğinden).
    ``enrich_bku=true`` ise ml/bku_mrl_active_map.json eşlemesiyle BKÜ canlı MRL tablosundan örnek satırlar eklenir.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Yalnızca görsel dosyası yükleyin (image/*).")

    raw = await file.read()
    if not raw or len(raw) < 256:
        raise HTTPException(status_code=400, detail="Dosya boş veya çok küçük.")

    try:
        data = await asyncio.to_thread(prepare_plant_image_bytes, raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Görsel hazırlama hatası: {e}")
        raise HTTPException(status_code=400, detail="Görsel işlenemedi.") from e

    try:
        # CNN CPU inference — event loop'u bloklamasın (ardışık isteklerde timeout/502 önlenir)
        prediction = await asyncio.to_thread(
            plant_analysis_service.predict_image_bytes, data
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        ) from e

    payload = plant_analysis_service.build_payload(prediction)

    if enrich_bku and payload.get("detected", True):
        try:
            payload = await asyncio.wait_for(
                attach_bku_mrl(payload),
                timeout=20.0,
            )
        except asyncio.TimeoutError:
            logger.warning("BKÜ zenginleştirme zaman aşımı (20s); CNN sonucu yine döndürülüyor.")
            payload["bkuMrlEnrichment"] = {
                "enabled": True,
                "resolvedSubstances": [],
                "errors": ["bku_timeout"],
                "infoTr": "BKÜ tablosu şu an yanıt vermedi; tekrar deneyin.",
            }

    if enrich_llm and payload.get("detected", True):
        narrative = plant_analysis_service.enrich_with_llm(payload)
        payload["narrativeSummary"] = narrative

    return payload


@router.get("/weather")
async def weather_endpoint(
    lat: float,
    lon: float,
    current_user: dict = Depends(get_current_user),
):
    """Anlık hava durumu ve konum bilgisi."""
    if settings.SIMULATION_MODE:
        lat, lon = get_random_urfa_location()

    weather, location = await fetch_weather_and_location(lat, lon)

    if weather:
        return {**weather, "location": location}
    raise HTTPException(status_code=404, detail="Hava durumu verisi alınamadı")


@router.post("/tools/generate-map", response_class=HTMLResponse)
async def generate_map_html(req: MapRequest):
    """Verilen şehir için interaktif Folium haritası HTML'i üretir."""
    try:
        geolocator = Nominatim(user_agent="ciftci_app")
        location = geolocator.geocode(req.city)

        if not location:
            raise HTTPException(status_code=404, detail="Şehir bulunamadı")

        m = folium.Map(location=[location.latitude, location.longitude], zoom_start=12)
        MiniMap().add_to(m)
        folium.Marker(
            [location.latitude, location.longitude],
            popup=req.city,
        ).add_to(m)

        logger.info(f"Harita oluşturuldu: {req.city}")
        return m._repr_html_()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Harita oluşturma hatası: {e}")
        raise HTTPException(status_code=500, detail="Harita oluşturulamadı")
