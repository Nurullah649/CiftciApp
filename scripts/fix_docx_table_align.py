"""Tablo 2 sola kaymayi duzelt: tablo genisligi %100, hizalama sol."""
from __future__ import annotations

import zipfile
from pathlib import Path

import xml.etree.ElementTree as ET

SRC = Path(r"C:\Users\agdbe\Downloads\Bitirme-2_AraRapor_KTUN (1).docx")
DST = Path(r"C:\Users\agdbe\Downloads\Bitirme-2_AraRapor_KTUN_DUZGUN.docx")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def para_text(p: ET.Element) -> str:
    return "".join(t.text or "" for t in p.iter(W + "t")).strip()


def table_signature(tbl: ET.Element) -> str:
    parts = [para_text(p) for p in tbl.iter(W + "p")]
    return " ".join(t for t in parts if t)[:200]


def ensure_tbl_pr(tbl: ET.Element) -> ET.Element:
    pr = tbl.find(W + "tblPr")
    if pr is None:
        pr = ET.Element(W + "tblPr")
        tbl.insert(0, pr)
    return pr


def set_full_width_left(tbl: ET.Element) -> None:
    pr = ensure_tbl_pr(tbl)
    for old in pr.findall(W + "tblW"):
        pr.remove(old)
    for old in pr.findall(W + "jc"):
        pr.remove(old)
    for old in pr.findall(W + "tblInd"):
        pr.remove(old)
    tw = ET.SubElement(pr, W + "tblW")
    tw.set(f"{W}type", "pct")
    tw.set(f"{W}w", "5000")  # %100
    jc = ET.SubElement(pr, W + "jc")
    jc.set(f"{W}val", "left")
    # Hucre kenar bosluklarini sifirla (ic ice tabloda kayma onlenir)
    for tc in tbl.findall(f".//{W}tc"):
        tcpr = tc.find(W + "tcPr")
        if tcpr is None:
            tcpr = ET.SubElement(tc, W + "tcPr")
            tc.insert(0, tcpr)
        for tag in (W + "tcMar", W + "tblCellMar"):
            for el in tcpr.findall(tag):
                tcpr.remove(el)


def fix_nested_wrapper_tables(root: ET.Element) -> list[str]:
    log: list[str] = []
    for tbl in root.iter(W + "tbl"):
        sig = table_signature(tbl)
        if "DÖNEM SONU" in sig or ("Hedef" in sig and "Durum" in sig and "Açıklama" in sig):
            set_full_width_left(tbl)
            label = "Tablo2-icerik" if "Hedef" in sig else "Donem-sonu-sarmal"
            log.append(f"{label}: genislik %100, sola hizalandi")
    return log


def fix_outer_content_table(root: ET.Element) -> None:
    """Ana 1x1 materyal tablosu da tam genislik."""
    for tbl in root.iter(W + "tbl"):
        sig = table_signature(tbl)
        if sig.startswith("PROJEDE KULLANILAN") or "MATERYAL VE METOTLAR" in sig[:80]:
            set_full_width_left(tbl)


def main() -> None:
    if not SRC.is_file():
        print(f"[HATA] {SRC}")
        return

    with zipfile.ZipFile(SRC, "r") as zin:
        with zipfile.ZipFile(DST, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/document.xml":
                    root = ET.fromstring(data)
                    fix_outer_content_table(root)
                    logs = fix_nested_wrapper_tables(root)
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                zout.writestr(item, data)

    print(f"[OK] {DST}")
    for x in logs:
        print(f"     {x}")


if __name__ == "__main__":
    main()
