"""Word ara rapor dosyasındaki şekil sırasını ve gömülü görselleri listeler."""
from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

DOCX = Path(r"C:\Users\agdbe\Downloads\Bitirme-2_AraRapor_KTUN (1).docx")
OUT = Path(__file__).resolve().parents[1] / "ml" / "report" / "docx_check.txt"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"


def main() -> None:
    lines: list[str] = []
    with zipfile.ZipFile(DOCX) as z:
        media = sorted(n for n in z.namelist() if n.startswith("word/media/"))
        lines.append(f"Dosya: {DOCX}")
        lines.append(f"Gomulu gorsel sayisi: {len(media)}")
        for m in media:
            data = z.read(m)
            lines.append(f"  {m} ({len(data) // 1024} KB)")

        rels = ET.fromstring(z.read("word/_rels/document.xml.rels"))
        rid_to_target = {
            rel.get("Id"): rel.get("Target")
            for rel in rels
            if rel.tag.endswith("Relationship")
        }

        doc = ET.fromstring(z.read("word/document.xml"))
        body = doc.find(W + "body")
        if body is None:
            lines.append("body bulunamadi")
            OUT.write_text("\n".join(lines), encoding="utf-8")
            return

        lines.append("\n--- Metin + gorsel akisi ---")
        idx = 0
        for para in doc.iter(W + "p"):
            texts: list[str] = []
            imgs: list[str] = []
            for t in para.iter(W + "t"):
                if t.text:
                    texts.append(t.text)
            for blip in para.iter(A + "blip"):
                rid = blip.get(RID)
                if rid:
                    imgs.append(rid_to_target.get(rid, "?"))
            line = "".join(texts).strip()
            if line or imgs:
                idx += 1
                img_note = f" [GORSEL: {', '.join(imgs)}]" if imgs else ""
                lines.append(f"{idx:3}{img_note} {line[:200]}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT)
    print(f"Satir: {len(lines)}")


if __name__ == "__main__":
    main()
