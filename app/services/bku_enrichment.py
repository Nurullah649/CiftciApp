"""analyze-plant çıktısına BKÜ MRL tablosu ekler (etken madde → Details ID eşlemesi ile)."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.services.bku_client import BKU_DEFAULT_HEADERS, fetch_mrl_datatable_json


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def _normalize_lookup_token(raw: str) -> str:
    s = raw.strip().lower().translate(_TR_ASCII)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def _strip_paren_notes(name: str) -> str:
    return re.sub(r"\([^)]*\)", " ", name).strip()


def _split_ingredient_phrase(name: str) -> List[str]:
    base = _strip_paren_notes(name)
    parts = re.split(r"\s*(?:veya|\+|/|,)\s*", base, flags=re.IGNORECASE)
    out: List[str] = []
    for p in parts:
        q = p.strip()
        if not q:
            continue
        q = re.sub(r"\s*\(.*", "", q).strip()
        q = re.sub(r"\s+kombine\s*$", "", q, flags=re.IGNORECASE).strip()
        if q:
            out.append(q)
    return out


_map_cache: Optional[Dict[str, Any]] = None


def load_map_file() -> Dict[str, Any]:
    """BKÜ token→Details ID haritasını yükle (startup veya ilk istek)."""
    global _map_cache
    if _map_cache is not None:
        return _map_cache

    raw_path = settings.BKU_MRL_MAP_PATH
    path = Path(raw_path) if raw_path else _project_root() / "ml" / "bku_mrl_active_map.json"
    if not path.is_file():
        logger.warning(f"bku_mrl_active_map.json bulunamadı: {path}")
        _map_cache = {"_meta": {}, "tokens": {}}
        return _map_cache

    try:
        _map_cache = json.loads(path.read_text(encoding="utf-8"))
        if "tokens" not in _map_cache:
            _map_cache["tokens"] = {}
        return _map_cache
    except Exception as e:
        logger.error(f"BKÜ harita JSON okunamadı: {e}")
        _map_cache = {"_meta": {}, "tokens": {}, "_error": str(e)}
        return _map_cache


def reset_map_cache_for_tests() -> None:
    global _map_cache
    _map_cache = None


def map_token_count() -> int:
    data = load_map_file()
    return len(data.get("tokens") or {})


def resolve_detail_ids_for_payload(active_ingredients: Iterable[Dict[str, Any]]) -> Tuple[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Etken madde satırlarından BKÜ MRL detay kimliklerini çıkarır.

    Returns:
      resolved: detail_id -> {matched_tokens: [...], matched_from_phrases: [...]}
      failures: [{phrase tokens..., reason}]
    """
    token_map: Dict[str, Any] = load_map_file().get("tokens") or {}
    resolved: Dict[int, Dict[str, Any]] = {}
    failures: List[Dict[str, Any]] = []

    for row in active_ingredients:
        phrase = str(row.get("name") or "")
        pieces = _split_ingredient_phrase(phrase)
        if not pieces:
            continue

        phrase_hits: List[int] = []
        for piece in pieces:
            nt = _normalize_lookup_token(piece)
            if not nt:
                continue
            bid = token_map.get(nt)
            if bid is None:
                continue
            try:
                iid = int(bid)
            except (TypeError, ValueError):
                continue
            phrase_hits.append(iid)
            bucket = resolved.setdefault(iid, {"matched_tokens": [], "matched_from_phrases": []})
            if nt not in bucket["matched_tokens"]:
                bucket["matched_tokens"].append(nt)
            if phrase not in bucket["matched_from_phrases"]:
                bucket["matched_from_phrases"].append(phrase)

        if not phrase_hits and phrase.strip():
            failures.append(
                {
                    "phrase": phrase,
                    "normalizedPieces": [_normalize_lookup_token(p) for p in pieces],
                    "reason": "no_token_match_in_map",
                }
            )

    return resolved, failures


def compact_bku_for_llm(block: Optional[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """LLM prompt token tasarrufu için BKÜ bloğunu küçült."""
    if not block or not block.get("enabled"):
        return None
    slim: List[Dict[str, Any]] = []
    for s in (block.get("resolvedSubstances") or [])[:5]:
        slim.append(
            {
                "detailUrl": s.get("detailUrl"),
                "ornekleme": (s.get("sampleRows") or [])[:6],
            }
        )
    return slim or None


def _prefer_ruhsat_rows(rows: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    lic: List[Dict[str, Any]] = []
    other: List[Dict[str, Any]] = []
    for r in rows:
        durum = str(r.get("durumu") or "")
        if "ruhsat" in durum.lower():
            lic.append(r)
        else:
            other.append(r)
    merged = lic + other
    return merged[:limit]


async def attach_bku_mrl(payload: Dict[str, Any]) -> Dict[str, Any]:
    """payload içine bkuMrlEnrichment ekler (veya hata özeti)."""
    meta = load_map_file().get("_meta") or {}
    base_url = settings.BKU_BASE_URL.rstrip("/")

    ingredients = payload.get("activeIngredients") or []
    resolved_map, failures = resolve_detail_ids_for_payload(ingredients)

    if not resolved_map:
        payload["bkuMrlEnrichment"] = {
            "enabled": True,
            "sourceHomepage": meta.get("official_site") or "https://bku.tarimorman.gov.tr/Arama/Index",
            "resolvedSubstances": [],
            "lookupFailures": failures,
            "infoTr": meta.get("note_tr"),
            "disclaimerTr": meta.get("disclaimer_tr"),
        }
        return payload

    sem = asyncio.Semaphore(2)

    async def one_substance(detail_id: int, trace: Dict[str, Any]) -> Dict[str, Any]:
        async with sem:
            async with httpx.AsyncClient(headers=BKU_DEFAULT_HEADERS, follow_redirects=True, timeout=settings.BKU_TIMEOUT_SECONDS) as client:
                raw = await fetch_mrl_datatable_json(
                    client,
                    base_url=base_url,
                    mrl_aktif_madde_detail_id=detail_id,
                    max_rows=settings.BKU_MAX_ROWS_PER_SUBSTANCE,
                )
            rows = list(raw.get("data") or [])
            detail_url = f"{base_url}/MRLAktifMadde/Details/{detail_id}"
            sample = _prefer_ruhsat_rows(rows, limit=min(25, settings.BKU_MAX_ROWS_PER_SUBSTANCE))
            return {
                "detailId": detail_id,
                "detailUrl": detail_url,
                "matchedFromIngredients": trace.get("matched_from_phrases") or [],
                "matchedTokens": trace.get("matched_tokens") or [],
                "recordsTotal": raw.get("recordsTotal"),
                "recordsFiltered": raw.get("recordsFiltered"),
                "sampleRows": sample,
            }

    tasks = [one_substance(iid, resolved_map[iid]) for iid in sorted(resolved_map.keys())]
    resolved_substances: List[Dict[str, Any]] = []
    errors: List[str] = []
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            errors.append(str(res))
            logger.warning(f"BKÜ MRL çekilemedi: {res}")
        else:
            resolved_substances.append(res)

    payload["bkuMrlEnrichment"] = {
        "enabled": True,
        "sourceHomepage": meta.get("official_site") or "https://bku.tarimorman.gov.tr/Arama/Index",
        "resolvedSubstances": resolved_substances,
        "lookupFailures": failures,
        "errors": errors or None,
        "infoTr": meta.get("note_tr"),
        "disclaimerTr": meta.get("disclaimer_tr"),
    }
    return payload
