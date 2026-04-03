"""
Hava Durumu ve Konum Servisi: WeatherAPI ve OpenCage Geocoding.
httpx ile async HTTP çağrıları yapar.
"""

import random
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.core.redis import cache_response


WEATHER_API_URL = "https://api.weatherapi.com/v1"
GEOCODING_API_URL = "https://api.opencagedata.com/geocode/v1"


def get_random_urfa_location() -> tuple[float, float]:
    """Simülasyon modu için rastgele Şanlıurfa koordinatı üretir."""
    lat = round(random.uniform(36.85, 37.25), 4)
    lon = round(random.uniform(38.60, 39.10), 4)
    return lat, lon


@cache_response(expire=1800)  # 30 minutes
async def fetch_weather(lat: float, lon: float) -> dict | None:
    """WeatherAPI'den anlık hava durumu verisini çeker."""
    lat, lon = round(lat, 2), round(lon, 2)
    if not settings.WEATHER_API_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{WEATHER_API_URL}/current.json",
                params={
                    "key": settings.WEATHER_API_KEY,
                    "q": f"{lat},{lon}",
                    "lang": "tr",
                },
            )
            data = response.json().get("current", {})
            return {
                "temp": data.get("temp_c"),
                "humidity": data.get("humidity"),
                "condition": data.get("condition", {}).get("text"),
                "wind": data.get("wind_kph"),
            }
    except Exception as e:
        logger.warning(f"Hava durumu alınamadı: {e}")
        return None


@cache_response(expire=86400)  # 24 hours
async def fetch_location_name(lat: float, lon: float) -> str:
    """OpenCage Geocoding API ile koordinattan adres çevirir."""
    lat, lon = round(lat, 3), round(lon, 3)
    if not settings.GEOCODING_API_KEY:
        return "Konum Servisi Kapalı"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{GEOCODING_API_URL}/json",
                params={
                    "q": f"{lat}+{lon}",
                    "key": settings.GEOCODING_API_KEY,
                    "language": "tr",
                    "no_annotations": 1,
                },
            )
            data = response.json()
            if data["results"]:
                return data["results"][0]["formatted"]
            return "Bilinmeyen Bölge"
    except Exception as e:
        logger.warning(f"Konum ismi alınamadı: {e}")
        return "Konum Bulunamadı"


async def fetch_weather_and_location(lat: float, lon: float) -> tuple[dict | None, str]:
    """Hava durumu ve konum bilgisini paralel olarak çeker (asyncio.gather)."""
    import asyncio

    weather, location = await asyncio.gather(
        fetch_weather(lat, lon),
        fetch_location_name(lat, lon),
    )
    return weather, location
