"""T.C. Tarım BKÜ (Bitki Koruma Ürünleri) — MRL aktif madde tablosu istemcisi."""

from __future__ import annotations

import re
from typing import Any, Dict

import httpx

_CSRF_RE = re.compile(r'name="__RequestVerificationToken"[^>]+value="([^"]+)"')

BKU_DEFAULT_HEADERS = {
    "User-Agent": "CiftciAppPlantAnalysis/1.0 (edu-research; +https://bku.tarimorman.gov.tr)",
    "Accept": "application/json, text/plain, */*",
}


async def fetch_mrl_datatable_json(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    mrl_aktif_madde_detail_id: int,
    max_rows: int = 80,
) -> Dict[str, Any]:
    """
    BKÜ MRL Aktif Madde detayı sayfası için DataTables JSON'unu çeker.

    Oturum çerezi + CSRF için önce GET Details/{id}, sonra POST MrlAktifeAitOranlariGetir gerekir.
    """
    root = base_url.rstrip("/")
    detail_url = f"{root}/MRLAktifMadde/Details/{int(mrl_aktif_madde_detail_id)}"

    pg = await client.get(detail_url)
    pg.raise_for_status()
    m = _CSRF_RE.search(pg.text)
    if not m:
        raise RuntimeError("BKÜ CSRF (__RequestVerificationToken) bulunamadı")

    token = m.group(1)
    post_url = f"{root}/MRLAktifMadde/MrlAktifeAitOranlariGetir"

    cols = ["mrlUrunAdi", "mrlOrani", "tarih", "aciklama"]
    cap = max(1, min(int(max_rows), 500))
    form: Dict[str, Any] = {
        "draw": "1",
        "start": "0",
        "length": str(cap),
        "search[value]": "",
        "search[regex]": "false",
        "order[0][column]": "0",
        "order[0][dir]": "desc",
        "Filtre.Id": str(int(mrl_aktif_madde_detail_id)),
        "__RequestVerificationToken": token,
    }

    for i, col in enumerate(cols):
        form[f"columns[{i}][data]"] = col
        form[f"columns[{i}][name]"] = ""
        form[f"columns[{i}][searchable]"] = "true"
        form[f"columns[{i}][orderable]"] = "false" if col in ("mrlOrani", "aciklama") else "true"
        form[f"columns[{i}][search][value]"] = ""
        form[f"columns[{i}][search][regex]"] = "false"

    r = await client.post(post_url, data=form, headers={"Referer": detail_url})
    r.raise_for_status()
    return r.json()
