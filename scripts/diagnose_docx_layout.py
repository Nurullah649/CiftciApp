"""Word docx yapisini analiz eder — tablo icinde mi, yuzan gorsel mi, vb."""
from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

DOCX = Path(r"C:\Users\agdbe\Downloads\Bitirme-2_AraRapor_KTUN (1).docx")
OUT = Path(__file__).resolve().parents[1] / "ml" / "report" / "docx_layout_diagnosis.txt"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"


def para_text(p) -> str:
    return "".join(t.text or "" for t in p.iter(W + "t")).strip()


def para_flags(p) -> list[str]:
    flags: list[str] = []
    ppr = p.find(W + "pPr")
    if ppr is None:
        return flags
    if ppr.find(W + "keepNext") is not None:
        flags.append("keepNext")
    if ppr.find(W + "keepLines") is not None:
        flags.append("keepLines")
    if ppr.find(W + "pageBreakBefore") is not None:
        flags.append("pageBreakBefore")
    spacing = ppr.find(W + "spacing")
    if spacing is not None and spacing.get(f"{W}after"):
        flags.append(f"spaceAfter={spacing.get(f'{W}after')}")
    return flags


def has_image(p) -> bool:
    return any(True for _ in p.iter(A + "blip"))


def image_wrap(p) -> str:
    for drawing in p.iter(W + "drawing"):
        if drawing.find(f".//{WP}inline") is not None:
            return "inline"
        anchor = drawing.find(f".//{WP}anchor")
        if anchor is not None:
            behind = anchor.get("behindDoc", "0")
            return f"anchor(behindDoc={behind})"
    return ""


def has_page_break(p) -> bool:
    for br in p.iter(W + "br"):
        if br.get(f"{W}type") == "page":
            return True
    return False


def walk_body(body, lines: list[str], depth: int = 0, in_table: bool = False, table_path: str = "") -> None:
    indent = "  " * depth
    for child in body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "tbl":
            rows = child.findall(W + "tr")
            cols = len(rows[0].findall(W + "tc")) if rows else 0
            lines.append(f"{indent}[TABLO basla: {len(rows)} satir x ~{cols} sutun]")
            for ri, tr in enumerate(rows):
                for ci, tc in enumerate(tr.findall(W + "tc")):
                    cell_path = f"tablo[r{ri+1}c{ci+1}]"
                    for sub in tc:
                        walk_body([sub], lines, depth + 1, True, cell_path)
            lines.append(f"{indent}[TABLO bitis]")
            continue

        if tag == "p":
            text = para_text(child)
            flags = para_flags(child)
            img = has_image(child)
            wrap = image_wrap(child) if img else ""
            pb = has_page_break(child)
            loc = f" IN:{table_path}" if in_table else ""
            parts = []
            if img:
                parts.append(f"GORSEL({wrap or '?'})")
            if pb:
                parts.append("SAYFA_SONU")
            if flags:
                parts.append(",".join(flags))
            meta = f" [{' | '.join(parts)}]" if parts else ""
            if text or img or pb:
                preview = text[:120] if text else "(bos paragraf)"
                lines.append(f"{indent}P{loc}{meta} {preview}")
            continue

        if tag == "sectPr":
            lines.append(f"{indent}[BOLUM AYARI / sayfa sonu ayarlari]")
            continue

        if tag in ("sdt", "customXml", "bookmarkStart", "bookmarkEnd"):
            for sub in child:
                walk_body([sub], lines, depth, in_table, table_path)


def main() -> None:
    lines: list[str] = [f"Dosya: {DOCX}", "=" * 60, ""]
    with zipfile.ZipFile(DOCX) as z:
        doc = ET.fromstring(z.read("word/document.xml"))
        body = doc.find(W + "body")
        if body is None:
            print("body yok")
            return

        # Ozet: tablo sayisi
        tables = list(body.iter(W + "tbl"))
        anchors = list(body.iter(f"{WP}anchor"))
        inlines = list(body.iter(f"{WP}inline"))
        lines.append(f"Toplam tablo: {len(tables)}")
        lines.append(f"Inline gorsel: {len(inlines)}, Anchor (yuzan) gorsel: {len(anchors)}")
        lines.append("")

        # Sekil 7-12 bolgesi
        lines.append("=" * 60)
        lines.append("SEKIL 7-12 BOLGESI (detay)")
        lines.append("=" * 60)
        walk_body(body, lines)

        all_lines: list[str] = []
        walk_body(body, all_lines)

        lines.append("")
        lines.append("=" * 60)
        lines.append("SEKIL 8 CEVRESI (filtre)")
        lines.append("=" * 60)
        for i, ln in enumerate(all_lines):
            low = ln.lower()
            if "ekil 7" in low or "ekil 8" in low or "ekil 9" in low or "tablo" in low and "gor" in low:
                start = max(0, i - 4)
                end = min(len(all_lines), i + 10)
                lines.extend(all_lines[start:end])
                lines.append("---")

        # teshis
        lines.append("")
        lines.append("=" * 60)
        lines.append("TESHIS")
        lines.append("=" * 60)
        fig8_in_table = any("ekil 8" in ln.lower() and "IN:tablo" in ln for ln in all_lines)
        any_in_table = any("IN:tablo" in ln and "GORSEL" in ln for ln in all_lines)

        if fig8_in_table:
            lines.append(">>> SORUN: Sekil 8 veya altindaki yazi TABLO HUCRESININ ICINDE.")
            lines.append("    Enter tabloya yeni satir ekler; baska sayfaya gecmez.")
            lines.append("    COZUM: Sol ust kose ok ile tabloyu sec > Delete. Icerigi tablo DISINA yapistir.")
        elif any_in_table:
            lines.append(">>> SORUN: Sekil 7-12 grafikleri TABLO ICINDE.")
            lines.append("    COZUM: Tum grafikleri tablo disina kes-yapistir ile tasi.")
        if anchors:
            lines.append(f">>> {len(anchors)} YUZAN gorsel: Metin kaydirma > Metinle ayni hizada yap.")
        if not fig8_in_table and not any_in_table:
            lines.append("Sekil 8 duz metinde. Muhtemel neden: dev tablo veya keepNext.")
            lines.append("COZUM: Sekil 8 yazisinin USTUNE tikla > Ctrl+Enter (sayfa sonu).")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT)
    for ln in lines[-15:]:
        print(ln)


if __name__ == "__main__":
    main()
