"""Belirli alt string için Details ID ara."""
from __future__ import annotations

import asyncio
import re

import httpx

BASE = "https://bku.tarimorman.gov.tr"
HDR = {"User-Agent": "CiftciAppPlantAnalysis/1.0"}
CSRF = re.compile(r'name="__RequestVerificationToken"[^>]+value="([^"]+)"')
NEEDLES = ["chlorothalonil", "clorotalonil", "propiconazole", "propikonazol", "tebuconazole", "tebukonazol", "piraclostrobin", "piraklostrobin"]


async def main() -> None:
    async with httpx.AsyncClient(headers=HDR, follow_redirects=True, timeout=15) as client:
        for did in range(1, 501):
            r = await client.get(f"{BASE}/MRLAktifMadde/Details/{did}")
            if r.status_code != 200 or not CSRF.search(r.text):
                continue
            low = r.text.lower()
            for n in NEEDLES:
                if n in low:
                    print(did, n)


if __name__ == "__main__":
    asyncio.run(main())
