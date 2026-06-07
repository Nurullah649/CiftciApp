"""BKÜ MRL Aktif Madde Details ID keşfi (tek seferlik yardımcı script)."""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

import httpx

BASE = "https://bku.tarimorman.gov.tr"
HDR = {"User-Agent": "CiftciAppPlantAnalysis/1.0"}
CSRF = re.compile(r'name="__RequestVerificationToken"[^>]+value="([^"]+)"')

SEARCH_TERMS = [
    "azoksistrobin",
    "azoxystrobin",
    "mancozeb",
    "clorotalonil",
    "chlorothalonil",
    "metalaksil",
    "metalaxyl",
    "propikonazol",
    "propiconazole",
    "difenokonazol",
    "abamektin",
    "abamectin",
    "kukurt",
    "sulfur",
    "captan",
    "myclobutanil",
    "cimoksanil",
    "cymoxanil",
    "bakir",
    "copper",
]


async def genel_search(client: httpx.AsyncClient, q: str) -> List[Dict[str, Any]]:
    await client.get(f"{BASE}/Arama/Index")
    r = await client.get(
        f"{BASE}/Tamamla/GenelAramaKelimesiGetir5",
        params={"query": q},
        headers={"Referer": f"{BASE}/Arama/Index"},
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


async def details_ok(client: httpx.AsyncClient, detail_id: int) -> tuple[bool, Optional[str]]:
    r = await client.get(f"{BASE}/MRLAktifMadde/Details/{detail_id}")
    if r.status_code != 200:
        return False, None
    if not CSRF.search(r.text):
        return False, None
    m = re.search(r"<h2[^>]*>([^<]{5,120})</h2>", r.text, re.I)
    title = m.group(1).strip() if m else None
    return True, title


async def mrl_oran_search(client: httpx.AsyncClient, q: str) -> List[Dict[str, Any]]:
    await client.get(f"{BASE}/MRLOrani/Index")
    r = await client.get(
        f"{BASE}/Tamamla/MrlOraniSecimListesiGetir",
        params={"pageSize": 25, "id": q},
        headers={"Referer": f"{BASE}/MRLOrani/Index"},
    )
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        return data
    return data.get("results") or []


async def probe_range(client: httpx.AsyncClient, start: int, end: int) -> Dict[int, str]:
    found: Dict[int, str] = {}
    for did in range(start, end + 1):
        ok, title = await details_ok(client, did)
        if ok and title:
            found[did] = title
            print(f"  Details/{did}: {title[:80]}")
    return found


async def main() -> None:
    results: Dict[str, Any] = {"by_search": {}, "valid_details": {}}

    async with httpx.AsyncClient(headers=HDR, follow_redirects=True, timeout=30) as client:
        for q in SEARCH_TERMS:
            items = await genel_search(client, q)
            mrl_items = [i for i in items if "MRL Aktif Madde" in str(i.get("Name", ""))]
            results["by_search"][q] = mrl_items
            print(f"\n=== {q} ({len(mrl_items)} MRL hits) ===")
            for item in mrl_items[:5]:
                iid = int(item["Id"])
                ok, title = await details_ok(client, iid)
                print(f"  GenelArama Id={iid} details_ok={ok} title={title or item.get('Name','')[:60]}")

        print("\n=== Scanning Details 1-120 for known names ===")
        found = await probe_range(client, 1, 120)
        results["valid_details"] = found

    out = Path(__file__).resolve().parents[1] / "ml" / "bku_mrl_discovery.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    from pathlib import Path

    asyncio.run(main())
