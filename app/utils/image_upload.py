"""Yüklenen bitki fotoğraflarını CNN için küçültür (nginx/API boyut limiti)."""

from __future__ import annotations

import io

from fastapi import HTTPException
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

# Nginx client_max_body_size ile uyumlu üst sınır (ham yükleme)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
# İşlenmiş JPEG hedefi
TARGET_MAX_SIDE = 1024
TARGET_MAX_BYTES = 900_000


def prepare_plant_image_bytes(data: bytes) -> bytes:
    """
    Ham multipart gövdesini RGB JPEG'e çevirir ve yeniden boyutlandırır.
    Model zaten 224px kullanır; 1024 yeterli detay sağlar.
    """
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Görsel çok büyük ({len(data) // (1024 * 1024)} MB). En fazla 20 MB yükleyin.",
        )

    try:
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Geçersiz görsel dosyası.") from e

    w, h = img.size
    if max(w, h) > TARGET_MAX_SIDE:
        ratio = TARGET_MAX_SIDE / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

    for quality in (85, 75, 65):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        out = buf.getvalue()
        if len(out) <= TARGET_MAX_BYTES:
            return out

    return out
