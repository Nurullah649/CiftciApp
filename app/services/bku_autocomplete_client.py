"""BKÜ autocomplete JSON çağrıları (oturum çerezi için referer GET)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.services.bku_catalog import SLUG_MAP
from app.services.bku_client import BKU_DEFAULT_HEADERS


async def fetch_autocomplete(slug: str, q: str, *, mrl_detail_id: Optional[int] = None) -> Dict[str, Any]:
    """slug + arama metni ile BKÜ autocomplete JSON döner."""
    entry = SLUG_MAP.get(slug)
    if entry is None:
        raise ValueError(f"Bilinmeyen BKÜ slug: {slug}")

    term = q.strip()
    if len(term) < 2:
        raise ValueError("Arama metni en az 2 karakter olmalıdır.")

    root = settings.BKU_BASE_URL.rstrip("/")
    referer_path = entry.referer_path
    if slug == "mrl_aktif_madde_detay_secim" and mrl_detail_id is not None:
        referer_path = f"/MRLAktifMadde/Details/{int(mrl_detail_id)}"

    async with httpx.AsyncClient(
        headers=BKU_DEFAULT_HEADERS,
        follow_redirects=True,
        timeout=settings.BKU_TIMEOUT_SECONDS,
    ) as client:
        ref = root + referer_path
        await client.get(ref)

        if entry.param_style == "query":
            params: Dict[str, Any] = {"query": term}
        else:
            params = {"pageSize": 25, "id": term}

        url = root + entry.autocomplete_path
        r = await client.get(url, params=params, headers={"Referer": ref})
        r.raise_for_status()
        try:
            payload = r.json()
        except Exception as e:
            logger.warning(f"BKÜ autocomplete JSON parse: {e}")
            raise RuntimeError("BKÜ yanıtı JSON değil") from e

    if not isinstance(payload, list):
        payload = [payload]

    return {
        "slug": entry.slug,
        "title_tr": entry.title_tr,
        "autocomplete_path": entry.autocomplete_path,
        "referer_path": referer_path,
        "param_style": entry.param_style,
        "items": payload,
        "item_count": len(payload),
        "related_datatable_post_path": entry.related_datatable_post,
    }


def list_slugs() -> List[str]:
    return sorted(SLUG_MAP.keys())
