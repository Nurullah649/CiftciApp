"""Tablo 2 ve Dönem Sonu bolumunun sola kayma nedenini analiz eder."""
from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

for name in (
    "Bitirme-2_AraRapor_KTUN (1).docx",
    "Bitirme-2_AraRapor_KTUN_DUZGUN.docx",
):
    path = Path(rf"C:\Users\agdbe\Downloads\{name}")
    if not path.is_file():
        continue

    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

    def para_text(p):
        return "".join(t.text or "" for t in p.iter(W + "t")).strip()

    print(f"\n{'='*60}\n{name}\n{'='*60}")
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))

    tbl_idx = 0
    for tbl in root.iter(W + "tbl"):
        texts = [para_text(p) for p in tbl.iter(W + "p")]
        joined = " | ".join(t for t in texts if t)[:120]
        if "Tablo 2" in joined or "DÖNEM SONU" in joined or "Hedef" in joined and "Durum" in joined:
            tbl_idx += 1
            tbl_pr = tbl.find(W + "tblPr")
            ind = tbl_pr.find(W + "tblInd") if tbl_pr is not None else None
            jc = tbl_pr.find(W + "jc") if tbl_pr is not None else None
            ind_val = ind.get(f"{W}w") if ind is not None else "yok"
            jc_val = jc.get(f"{W}val") if jc is not None else "yok"
            rows = len(tbl.findall(W + "tr"))
            cols = len(tbl.findall(W + "tr")[0].findall(W + "tc")) if tbl.findall(W + "tr") else 0
            print(f"  Tablo: {rows}x{cols} | tblInd={ind_val} | jc={jc_val}")
            print(f"  Icerik: {joined[:100]}...")

            # ust tablo icinde mi?
            parent_chain = "body"
            print(f"  (nested tablo - icerikte Tablo2/Dönem Sonu eslesmesi)")

    # DÖNEM SONU paragrafi ve tblInd tum tablolar
    print("\n  --- Tum tablolar tblInd / jc ---")
    for i, tbl in enumerate(root.iter(W + "tbl")):
        tbl_pr = tbl.find(W + "tblPr")
        ind = tbl_pr.find(W + "tblInd") if tbl_pr is not None else None
        jc = tbl_pr.find(W + "jc") if tbl_pr is not None else None
        ind_val = ind.get(f"{W}w") if ind is not None else "-"
        jc_val = jc.get(f"{W}val") if jc is not None else "-"
        first = ""
        for p in tbl.iter(W + "p"):
            t = para_text(p)
            if t:
                first = t[:50]
                break
        print(f"  #{i}: tblInd={ind_val} jc={jc_val} | {first}")

    # Dönem sonu paragrafi indent
    for p in root.iter(W + "p"):
        t = para_text(p)
        if "DÖNEM SONU" in t or t.startswith("Tablo 2"):
            ppr = p.find(W + "pPr")
            ind = ppr.find(W + "ind") if ppr is not None else None
            jc = ppr.find(W + "jc") if ppr is not None else None
            if ind is not None:
                print(f"\n  Paragraf '{t[:40]}' ind left={ind.get(f'{W}left')} hanging={ind.get(f'{W}hanging')}")
            if jc is not None:
                print(f"  Paragraf jc={jc.get(f'{W}val')}")
