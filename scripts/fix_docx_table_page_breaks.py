"""KTUN tablo korunur: gorselleri sayfaya sigdir + Sekil 9 oncesi sayfa sonu."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import xml.etree.ElementTree as ET

SRC = Path(r"C:\Users\agdbe\Downloads\Bitirme-2_AraRapor_KTUN (1).docx")
DST = Path(r"C:\Users\agdbe\Downloads\Bitirme-2_AraRapor_KTUN_DUZGUN.docx")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

# A4 icerik alani ~24 cm; baslik + sekil yazisi icin gorsel max ~19 cm
MAX_CY_EMU = 6_800_000  # ~18.8 cm


def para_text(p: ET.Element) -> str:
    return "".join(t.text or "" for t in p.iter(W + "t")).strip()


def has_image(p: ET.Element) -> bool:
    return any(True for _ in p.iter(f"{A}blip"))


def shrink_extents(root: ET.Element) -> int:
    n = 0
    for ext in root.iter(f"{A}ext"):
        cx = int(ext.get("cx", 0))
        cy = int(ext.get("cy", 0))
        if cy > MAX_CY_EMU and cy > 0:
            scale = MAX_CY_EMU / cy
            ext.set("cy", str(int(cy * scale)))
            ext.set("cx", str(int(cx * scale)))
            n += 1
    return n


def clear_breaks(p: ET.Element) -> None:
    ppr = p.find(W + "pPr")
    if ppr is not None:
        for tag in (W + "pageBreakBefore",):
            for el in ppr.findall(tag):
                ppr.remove(el)
    for r in p.findall(W + "r"):
        for br in list(r.findall(W + "br")):
            if br.get(f"{W}type") == "page":
                r.remove(br)


def page_break_before(p: ET.Element) -> None:
    ppr = p.find(W + "pPr")
    if ppr is None:
        ppr = ET.SubElement(p, W + "pPr")
        p.insert(0, ppr)
    if ppr.find(W + "pageBreakBefore") is None:
        ppr.append(ET.Element(W + "pageBreakBefore"))


def fix_figure_flow(root: ET.Element) -> list[str]:
    log: list[str] = []
    paras = list(root.iter(W + "p"))
    for i, p in enumerate(paras):
        clear_breaks(p)

    for i, p in enumerate(paras):
        if not has_image(p):
            continue
        nxt = para_text(paras[i + 1]) if i + 1 < len(paras) else ""
        m = re.match(r"^Şekil\s+(7|8|9|10|11|12)\.", nxt)
        if m and int(m.group(1)) >= 8:
            page_break_before(p)
            log.append(f"Sekil {m.group(1)} gorseli yeni sayfadan basliyor")
    return log


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
    for tag in (W + "tblW", W + "jc", W + "tblInd"):
        for el in pr.findall(tag):
            pr.remove(el)
    tw = ET.SubElement(pr, W + "tblW")
    tw.set(f"{W}type", "pct")
    tw.set(f"{W}w", "5000")
    jc = ET.SubElement(pr, W + "jc")
    jc.set(f"{W}val", "left")


def fix_table_alignment(root: ET.Element) -> list[str]:
    """Tablo 2 ve materyal tablosu sola kaymasin diye %100 genislik."""
    log: list[str] = []
    for tbl in root.iter(W + "tbl"):
        sig = table_signature(tbl)
        if "MATERYAL VE METOTLAR" in sig[:80]:
            set_full_width_left(tbl)
            log.append("Materyal tablosu: %100 genislik, sol")
        elif "DÖNEM SONU" in sig:
            set_full_width_left(tbl)
            log.append("Donem sonu sarmal tablo: %100 genislik, sol")
        elif "Hedef" in sig and "Durum" in sig and "Açıklama" in sig:
            set_full_width_left(tbl)
            log.append("Tablo 2: %100 genislik, sol")
    return log


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
                    shrunk = shrink_extents(root)
                    logs = fix_figure_flow(root)
                    alogs = fix_table_alignment(root)
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                zout.writestr(item, data)

    print(f"[OK] {DST}")
    print(f"     {shrunk} gorsel ~19 cm yukseklige kucultuldu")
    for x in logs:
        print(f"     {x}")
    for x in alogs:
        print(f"     {x}")
    print()
    print("Bu dosyayi ac. Ctrl+Enter KULLANMA.")


if __name__ == "__main__":
    main()
