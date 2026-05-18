"""BKÜ arama uçları — katalog ve autocomplete proxy."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.core.security import get_current_user
from app.services.bku_autocomplete_client import fetch_autocomplete, list_slugs
from app.services.bku_catalog import SLUG_MAP, catalog_public_dict
from app.services.bku_faq_fanout import faq_fanout_search

router = APIRouter(tags=["BKÜ"])


@router.get("/tools/bku/catalog")
async def bku_tools_catalog(current_user: dict = Depends(get_current_user)):
    """BKÜ modüllerine karşılık gelen autocomplete URL kataloğu (mobil / panel için)."""
    return catalog_public_dict(settings.BKU_BASE_URL)


@router.get("/tools/bku/autocomplete")
async def bku_tools_autocomplete(
    slug: str = Query(..., description="katalog slug (örn. genel_arama_motoru)"),
    q: str = Query(..., min_length=2, description="En az 2 karakter arama metni"),
    mrl_detail_id: Optional[int] = Query(
        None,
        description="Yalnızca slug=mrl_aktif_madde_detay_secim iken: referer /MRLAktifMadde/Details/{id}",
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    BKÜ'deki autocomplete JSON'unu proxy eder (CSRF gerektirmez).

    Slug listesi: ``GET /tools/bku/catalog``.
    """
    try:
        return await fetch_autocomplete(slug, q, mrl_detail_id=mrl_detail_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"BKÜ isteği başarısız: {e}") from e


@router.get("/tools/bku/slugs")
async def bku_tools_slugs(current_user: dict = Depends(get_current_user)):
    """Desteklenen slug anahtarları (kısa liste)."""
    return {"slugs": list_slugs()}


@router.get("/tools/bku/faq-search")
async def bku_tools_faq_search(
    q: str = Query(..., min_length=2, description="Arama metni (tüm modüllere aynı q gider)"),
    limit: int = Query(35, ge=8, le=80, description="Modül ve alt grup başına max öğe"),
    parallel: int = Query(4, ge=1, le=6, description="Eşzamanlı BKÜ istek üst sınırı"),
    slugs: Optional[str] = Query(
        None,
        description="Virgülle slug listesi (örn. genel_arama_motoru,ruhsatli_bku_indeks); boşsa varsayılan 6 modül",
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    BKÜ kullanıcı rehberindeki konular için **aynı anda** birden fazla autocomplete isteği atar:

    ruhsatlı ürün indeksi, MRL indeks seçimi, geçici tavsiye, tavsiye arama/alternatif ve genel arama motoru.
    Genel arama çıktısı bitki / zararlı / MRL / entegre / aktif madde / formülasyon başlıklarına göre ayrıştırılır.
    """
    slug_tuple = None
    if slugs:
        parts = tuple(s.strip() for s in slugs.split(",") if s.strip())
        if not parts:
            raise HTTPException(status_code=400, detail="slugs boş olamaz; slugları virgülle ayırın.")
        for s in parts:
            if s not in SLUG_MAP:
                raise HTTPException(status_code=400, detail=f"Bilinmeyen slug: {s}")
        slug_tuple = parts

    try:
        return await faq_fanout_search(
            q,
            slugs=slug_tuple,
            limit_per_bucket=limit,
            max_parallel=parallel,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"BKÜ faq-search başarısız: {e}") from e
