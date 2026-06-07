"""Details 1-120 sayfalarından madde adı çıkar ve hedef tokenlarla eşleştir."""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import httpx

BASE = "https://bku.tarimorman.gov.tr"
HDR = {"User-Agent": "CiftciAppPlantAnalysis/1.0"}
CSRF = re.compile(r'name="__RequestVerificationToken"[^>]+value="([^"]+)"')

# treatment JSON + İngilizce eşanlamlılar
WANT = {
    "azoksistrobin": ["azoxystrobin", "azoksistrobin"],
    "mancozeb": ["mancozeb", "dithiocarbamate"],
    "clorotalonil": ["chlorothalonil", "clorotalonil"],
    "metalaksil": ["metalaxyl", "metalaksil"],
    "propikonazol": ["propiconazole", "propikonazol"],
    "difenokonazol": ["difenoconazole", "difenokonazol"],
    "abamektin": ["abamectin", "abamektin"],
    "cimoksanil": ["cymoxanil", "cimoksanil"],
    "captan": ["captan"],
    "myclobutanil": ["myclobutanil"],
    "kukurt": ["sulfur", "kukurt", "sulphur"],
    "bakir": ["copper", "bakir", "bakır"],
}


async def page_text(client: httpx.AsyncClient, did: int) -> str | None:
    r = await client.get(f"{BASE}/MRLAktifMadde/Details/{did}")
    if r.status_code != 200 or not CSRF.search(r.text):
        return None
    return r.text


async def main() -> None:
    pages: dict[int, str] = {}
    mapping: dict[str, int] = {}

    async with httpx.AsyncClient(headers=HDR, follow_redirects=True, timeout=20) as client:
        for did in range(1, 401):
            html = await page_text(client, did)
            if not html:
                continue
            low = html.lower()
            for token, needles in WANT.items():
                if token in mapping:
                    continue
                if any(n.lower() in low for n in needles):
                    mapping[token] = did
                    pages[did] = low[:500]
                    print(f"  {token} -> Details/{did}")

    out = Path(__file__).resolve().parents[1] / "ml" / "bku_mrl_token_probe.json"
    out.write_text(json.dumps({"mapping": mapping}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", out)


if __name__ == "__main__":
    asyncio.run(main())
