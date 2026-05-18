"""
BKÜ — kullanıcı rehberi (Arama Motoru yardım metni) ile hizalı çoklu autocomplete isteği.

Tek bir ``q`` için birden fazla modül ucu paralel çağrılır; genel arama çıktısı başlıklara göre ayrıştırılır.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.services.bku_autocomplete_client import fetch_autocomplete

# BKÜ indeks/autocomplete uçları (mrl_aktif_madde_detay_secim hariç — sayfa-id gerektirir)
DEFAULT_FANOUT_SLUGS: Tuple[str, ...] = (
    "genel_arama_motoru",
    "ruhsatli_bku_indeks",
    "mrl_orani_indeks_secim",
    "gecici_tavsiye_alan_secim",
    "tavsiye_arama",
    "tavsiye_alternatif",
)

_TR_ASCII = str.maketrans(
    {
        "ı": "i",
        "İ": "i",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ş": "s",
        "Ş": "s",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
    }
)


def _fold(s: str) -> str:
    return str(s or "").strip().translate(_TR_ASCII).lower()


def _item_label(row: Dict[str, Any]) -> str:
    if "Name" in row:
        return str(row.get("Name") or "")
    if "text" in row:
        return str(row.get("text") or "")
    return ""


def _cap(items: List[Any], limit: int) -> List[Any]:
    if limit <= 0 or len(items) <= limit:
        return items
    return items[:limit]


def split_genel_arama_items(items: List[Dict[str, Any]], *, limit_per_bucket: int) -> Dict[str, Any]:
    """GenelArama JSON satırlarını rehber başlıklarına yakın alt gruplara böler."""
    buckets: Dict[str, List[Dict[str, Any]]] = {
        "bitki_adı": [],
        "zararlı_organizma_adı_ve_latince": [],
        "mrl_ürün_ve_aktif_madde_satırları": [],
        "entegre_mücadele_teknik_talimat": [],
        "aktif_madde_genel": [],
        "formülasyon": [],
        "diğer_ve_karışık": [],
    }

    for row in items:
        name = _item_label(row)
        f = _fold(name)

        placed = False
        if f.startswith("bitki:"):
            buckets["bitki_adı"].append(row)
            placed = True
        if "zararl" in f[:28] and "organizma" in f[:40]:
            buckets["zararlı_organizma_adı_ve_latince"].append(row)
            placed = True
        if f.startswith("entegre"):
            buckets["entegre_mücadele_teknik_talimat"].append(row)
            placed = True
        if f.startswith("mrl aktif madde:") or f.startswith("mrl ürün:") or f.startswith("mrl urun:"):
            buckets["mrl_ürün_ve_aktif_madde_satırları"].append(row)
            placed = True
        elif f.startswith("aktif madde:"):
            buckets["aktif_madde_genel"].append(row)
            placed = True
        if "formulasyon" in f[:18]:
            buckets["formülasyon"].append(row)
            placed = True

        if not placed:
            buckets["diğer_ve_karışık"].append(row)

    out: Dict[str, Any] = {}
    for k, v in buckets.items():
        out[k] = {
            "item_count": len(v),
            "items": _cap(v, limit_per_bucket),
        }
    out["_note_tr"] = (
        "Gruplar ``Name`` metnine göre sezgisel ayrıştırılır; BKÜ etiketleri değişirse güncellenmelidir."
    )
    return out


GUIDE_METADATA_TR: Dict[str, Dict[str, str]] = {
    "ruhsatlı_bitki_koruma_ürünü_formülasyon_aktif_madde": {
        "matches_user_help_tr": (
            "Ruhsatlı Bitki Koruma Ürün bilgileri — Bitki Koruma Ürünü / Formülasyon / Aktif Madde adı aramaları"
        ),
        "bkü_slug_kaynagi": "ruhsatli_bku_indeks → /BKURuhsat/IndeksSelect2ListesiGetir",
    },
    "zararlı_bitki_mrl_entegre_aktif_formülasyon_genel_motor": {
        "matches_user_help_tr": (
            "Zararlı (ad/latince), Bitki, MRL, Entegre Talimat, Aktif madde, Formülasyon — tek kutuda dönen önerilerin ayrıştırılması"
        ),
        "bkü_slug_kaynagi": "genel_arama_motoru → /Tamamla/GenelAramaKelimesiGetir5",
    },
    "mrl_oranları_bitki_ve_mrl_aktif_madde": {
        "matches_user_help_tr": "MRL Oran bilgileri — Bitki Adı ve MRL Aktif Madde Adı seçimi",
        "bkü_slug_kaynagi": "mrl_orani_indeks_secim → /Tamamla/MrlOraniSecimListesiGetir",
    },
    "geçici_tavsiye_alanı_bitki_zararlı_aktif": {
        "matches_user_help_tr": (
            "Geçici Tavsiye Alan ürün bilgileri — Bitki / Zararlı / Zararlı Latince / Aktif madde önerileri"
        ),
        "bkü_slug_kaynagi": "gecici_tavsiye_alan_secim → /BKUGeciciTavsiyeAlanlar/Select2ListesiGetir",
    },
    "tavsiye_arama_grid": {
        "matches_user_help_tr": "Tavsiye çizelgesi önerileri (bitki, zararlı, aktif madde, ruhsatlı BKÜ bağlantıları)",
        "bkü_slug_kaynagi": "tavsiye_arama → /Kullanim/TavsiyeAramaKelimesiGetir3",
    },
    "tavsiye_alternatif": {
        "matches_user_help_tr": "Tavsiye Alternatif çoklu seçim önerileri",
        "bkü_slug_kaynagi": "tavsiye_alternatif → /Kullanim/AlternatifCokluSelect2ListesiGetir",
    },
}


async def faq_fanout_search(
    q: str,
    *,
    slugs: Optional[Tuple[str, ...]] = None,
    limit_per_bucket: int = 35,
    max_parallel: int = 4,
) -> Dict[str, Any]:
    """
    ``q`` için seçilen slug'lara paralel autocomplete isteği atar ve rehber yapısında birleştirir.
    """
    term = q.strip()
    if len(term) < 2:
        raise ValueError("Arama metni en az 2 karakter olmalıdır.")

    use_slugs = slugs if slugs else DEFAULT_FANOUT_SLUGS
    sem = asyncio.Semaphore(max(1, max_parallel))

    async def one(slug: str) -> Tuple[str, Optional[Dict[str, Any]], Optional[str]]:
        async with sem:
            try:
                data = await fetch_autocomplete(slug, term)
                return slug, data, None
            except Exception as e:
                logger.warning(f"BKÜ faq fanout slug={slug}: {e}")
                return slug, None, str(e)

    results = await asyncio.gather(*[one(s) for s in use_slugs])

    module_snapshots: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    genel_items: List[Dict[str, Any]] = []

    for slug, data, err in results:
        if err:
            errors[slug] = err
            continue
        if not data:
            continue
        items = data.get("items") or []
        module_snapshots[slug] = {
            "title_tr": data.get("title_tr"),
            "item_count": len(items),
            "items": _cap(items, limit_per_bucket),
            "autocomplete_path": data.get("autocomplete_path"),
            "related_datatable_post_path": data.get("related_datatable_post_path"),
        }
        if slug == "genel_arama_motoru":
            genel_items = list(items)

    genel_split = split_genel_arama_items(genel_items, limit_per_bucket=limit_per_bucket)

    aligned = {
        "ruhsatlı_bitki_koruma_ürünü_formülasyon_aktif_madde": {
            **GUIDE_METADATA_TR["ruhsatlı_bitki_koruma_ürünü_formülasyon_aktif_madde"],
            "items": module_snapshots.get("ruhsatli_bku_indeks", {}).get("items", []),
            "item_count": module_snapshots.get("ruhsatli_bku_indeks", {}).get("item_count", 0),
        },
        "mrl_oranları_bitki_ve_mrl_aktif_madde": {
            **GUIDE_METADATA_TR["mrl_oranları_bitki_ve_mrl_aktif_madde"],
            "items": module_snapshots.get("mrl_orani_indeks_secim", {}).get("items", []),
            "item_count": module_snapshots.get("mrl_orani_indeks_secim", {}).get("item_count", 0),
        },
        "geçici_tavsiye_alanı_bitki_zararlı_aktif": {
            **GUIDE_METADATA_TR["geçici_tavsiye_alanı_bitki_zararlı_aktif"],
            "items": module_snapshots.get("gecici_tavsiye_alan_secim", {}).get("items", []),
            "item_count": module_snapshots.get("gecici_tavsiye_alan_secim", {}).get("item_count", 0),
        },
        "tavsiye_arama_grid": {
            **GUIDE_METADATA_TR["tavsiye_arama_grid"],
            "items": module_snapshots.get("tavsiye_arama", {}).get("items", []),
            "item_count": module_snapshots.get("tavsiye_arama", {}).get("item_count", 0),
        },
        "tavsiye_alternatif": {
            **GUIDE_METADATA_TR["tavsiye_alternatif"],
            "items": module_snapshots.get("tavsiye_alternatif", {}).get("items", []),
            "item_count": module_snapshots.get("tavsiye_alternatif", {}).get("item_count", 0),
        },
        "genel_arama_motoru_ayrıştırması": {
            **GUIDE_METADATA_TR["zararlı_bitki_mrl_entegre_aktif_formülasyon_genel_motor"],
            "alt_gruplar": genel_split,
            "tüm_satırlar_özeti": {
                "item_count": len(genel_items),
                "items": _cap(genel_items, limit_per_bucket),
            },
        },
    }

    return {
        "query": term,
        "sluglar": list(use_slugs),
        "rehbere_göre": aligned,
        "modül_özeti": module_snapshots,
        "modül_hataları": errors or None,
        "uyarı_tr": (
            "Bu uç birden fazla BKÜ isteği yapar; sık çağrı yapmayın. Tam tablolar (DataTables POST) dahil değildir."
        ),
    }
