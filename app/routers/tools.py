"""
Tools Router: Genel araçlar (health check, hava durumu, harita).
3 endpoint: health, weather, generate-map
"""

import folium
from folium.plugins import MiniMap
from geopy.geocoders import Nominatim

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.core.security import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.weather_service import (
    fetch_weather_and_location,
    get_random_urfa_location,
)
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
        "qdrant_connected": rag_service.connected,
        "database_connected": db_ok,
        "ram_usage_mb": round(llm_service.get_ram_usage(), 2),
    }


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
