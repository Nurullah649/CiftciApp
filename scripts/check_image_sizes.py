"""Docx icindeki gorsel boyutlarini listeler."""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

DOCX = Path(r"C:\Users\agdbe\Downloads\Bitirme-2_AraRapor_KTUN (1).docx")
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

with zipfile.ZipFile(DOCX) as z:
    root = ET.fromstring(z.read("word/document.xml"))

for i, ext in enumerate(root.iter(f"{A}ext")):
    cx, cy = ext.get("cx"), ext.get("cy")
    if cx and cy:
        cm_w = int(cx) / 914400 * 2.54
        cm_h = int(cy) / 914400 * 2.54
        if cm_h > 15:
            print(f"Gorsel#{i}: {cm_w:.1f} x {cm_h:.1f} cm")
