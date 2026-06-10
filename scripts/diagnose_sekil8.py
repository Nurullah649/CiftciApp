"""Sekil 8-9 civarindaki tablo/gorsel yapisini detayli analiz eder."""
from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

DOCX = Path(r"C:\Users\agdbe\Downloads\Bitirme-2_AraRapor_KTUN (1).docx")
# kullanici farkli dosyada calisiyorsa SAYFA_SONLU da kontrol
ALT = Path(r"C:\Users\agdbe\Downloads\Bitirme-2_AraRapor_KTUN_SAYFA_SONLU.docx")
OUT = Path(__file__).resolve().parents[1] / "ml" / "report" / "sekil8_diagnosis.txt"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def para_text(p) -> str:
    return "".join(t.text or "" for t in p.iter(W + "t")).strip()


def has_image(p) -> bool:
    return any(True for _ in p.iter(A + "blip"))


def has_page_break(p) -> bool:
    ppr = p.find(W + "pPr")
    if ppr is not None and ppr.find(W + "pageBreakBefore") is not None:
        return True
    for br in p.iter(W + "br"):
        if br.get(f"{W}type") == "page":
            return True
    return False


def cell_height(tc) -> str:
    tcpr = tc.find(W + "tcPr")
    if tcpr is None:
        return "-"
    h = tcpr.find(W + "tcH")
    if h is not None:
        return f"height={h.get(f'{W}val')} rule={h.get(f'{W}hRule','auto')}"
    return "auto"


def analyze_docx(path: Path, lines: list[str]) -> None:
    if not path.is_file():
        lines.append(f"[YOK] {path}")
        return
    lines.append(f"\n{'='*60}\nDOSYA: {path.name}\n{'='*60}")

    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))

    paras = list(root.iter(W + "p"))
    # Sekil 8 civari indeks bul
    idx8 = idx9 = None
    for i, p in enumerate(paras):
        t = para_text(p)
        if t.startswith("Şekil 8"):
            idx8 = i
        if t.startswith("Şekil 9"):
            idx9 = i

    lines.append(f"Toplam paragraf: {len(paras)}")
    lines.append(f"Sekil 8 para index: {idx8}, Sekil 9 para index: {idx9}")

    if idx8 is None:
        lines.append("Sekil 8 bulunamadi!")
        return

    start = max(0, idx8 - 6)
    end = min(len(paras), (idx9 or idx8) + 8)
    lines.append(f"\n--- Paragraf {start} .. {end} ---")
    for i in range(start, end):
        p = paras[i]
        t = para_text(p)
        flags = []
        if has_image(p):
            flags.append("GORSEL")
        if has_page_break(p):
            flags.append("SAYFA_SONU")
        if not t and not flags:
            flags.append("BOS_SATIR")
        meta = f"[{', '.join(flags)}]" if flags else ""
        lines.append(f"  {i:4d}{meta} {t[:100] or '(bos)'}")

    # Sekil 8-9 arasi bos paragraf sayisi
    if idx9:
        between = paras[idx8 + 1 : idx9]
        empty = sum(1 for p in between if not para_text(p) and not has_image(p))
        imgs = sum(1 for p in between if has_image(p))
        lines.append(f"\nSekil 8 ile 9 arasi: {len(between)} paragraf, {empty} bos, {imgs} gorsel")

    # Bos tablolari say
    lines.append("\n--- Bos / tek hucreli tablolar ---")
    for ti, tbl in enumerate(root.iter(W + "tbl")):
        rows = tbl.findall(W + "tr")
        texts = [para_text(p) for p in tbl.iter(W + "p")]
        non_empty = [t for t in texts if t]
        imgs = sum(1 for p in tbl.iter(W + "p") if has_image(p))
        if len(non_empty) <= 2 and len(rows) <= 3:
            lines.append(f"  Tablo#{ti}: {len(rows)} satir, metin={len(non_empty)}, gorsel={imgs}")
            for t in non_empty[:5]:
                lines.append(f"    -> {t[:80]}")

    # tcH buyuk hucreler
    lines.append("\n--- Sabit yukseklikli hucreler ---")
    for tc in root.iter(W + "tc"):
        h = cell_height(tc)
        if "height=" in h and "auto" not in h.lower():
            tcount = len([1 for p in tc.iter(W + "p") if para_text(p) or has_image(p)])
            lines.append(f"  {h}, icerik paragraf~{tcount}")


def main() -> None:
    lines: list[str] = ["SEKIL 8-9 DIAGNOSIS"]
    for p in (DOCX, ALT):
        analyze_docx(p, lines)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT)
    print(lines[-40:] if len(lines) > 40 else "\n".join(lines))


if __name__ == "__main__":
    main()
