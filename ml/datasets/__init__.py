"""Hibrit dataset entegrasyonu için ortak yardımcılar.

Bu modül, farklı kaynaklardan gelen plant disease dataset'lerini
ortak bir taksonomi ve dizin yapısına dönüştürmek için kullanılan
helper'ları içerir.

Birleşik taksonomi:
    <Crop>___<Condition>          ör. "Apple___Apple_scab", "Wheat___Yellow_rust"
    <Crop>___healthy              ör. "Tomato___healthy"

Birleşik dizin:
    ml/data/raw/<unified_class>/<source>__<id>.jpg
    örnek: ml/data/raw/Apple___Apple_scab/plantvillage_0a76__000123.JPG
           ml/data/raw/Apple___Apple_scab/plantdoc_abc123.jpg

Kaynak prefix'i dosya adında saklanır → analiz ve debug için faydalı.
"""

from __future__ import annotations

import hashlib
import io
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ML_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RAW_DIR = ML_DIR / "data" / "raw"
DEFAULT_EXTERNAL_DIR = ML_DIR / "data" / "external"

VALID_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def safe_dirname(name: str) -> str:
    """Dosya sistemi için güvenli dizin adı (Windows uyumlu)."""
    forbidden = '<>:"/\\|?*'
    out = "".join("_" if c in forbidden else c for c in name)
    out = out.strip().strip(".")
    while "__" in out and out.startswith("_"):
        out = out[1:]
    return out or "_"


def safe_filename(name: str, max_len: int = 100) -> str:
    forbidden = '<>:"/\\|?*'
    out = "".join("_" if c in forbidden else c for c in name)
    out = out.strip().strip(".")
    if len(out) > max_len:
        base, ext = out, ""
        if "." in out:
            base, _, ext = out.rpartition(".")
            ext = "." + ext
        out = base[: max_len - len(ext)] + ext
    return out or "_"


def short_hash(data: Union[bytes, str], n: int = 8) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.md5(data).hexdigest()[:n]


def list_images(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    return [
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in VALID_EXT
    ]


def list_images_recursive(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    return [
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in VALID_EXT
    ]


def write_image_bytes(content: bytes, dst: Path) -> bool:
    """Görsel byte'larını diske yaz. Bozuksa False döner."""
    try:
        from PIL import Image
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
    except Exception:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(content)
    return True


def copy_image(src: Path, dst: Path, validate: bool = False) -> bool:
    """Görseli kopyala. validate=True ise PIL ile aç-kapat doğrula."""
    if dst.exists():
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    if validate:
        try:
            from PIL import Image
            with Image.open(src) as img:
                img.verify()
        except Exception:
            return False
    shutil.copy2(src, dst)
    return True


def make_unified_id(source: str, original_name: str, idx: int) -> str:
    """Birleşik dosya adı üret: <source>__<hash>__<idx>.<ext>

    source: 'plantvillage', 'plantdoc', 'olive', 'wheat', 'cotton', 'sunflower'
    Bu, kaynak takibi ve duplicate kontrolü için dosya adında saklanır.
    """
    suffix = Path(original_name).suffix.lower() or ".jpg"
    if suffix not in VALID_EXT:
        suffix = ".jpg"
    h = short_hash(original_name, 6)
    return f"{source}__{h}__{idx:06d}{suffix}"


def extract_zip(
    zip_path: Path,
    out_dir: Path,
    members_filter=None,
) -> int:
    """Zip içeriğini out_dir'a aç. members_filter callable(name)->bool olursa filtreler."""
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            if members_filter is not None and not members_filter(name):
                continue
            target = out_dir / name.replace("\\", "/")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted += 1
    return extracted


def extract_rar(rar_path: Path, out_dir: Path) -> int:
    """RAR arşivini extract et. Sırayla dener:
        1. rarfile (Python wrapper, unrar exe gerekir)
        2. patoolib (otomatik tool seçimi)
        3. 7z executable (sistemde 7z varsa)
    Başarısızsa 0 döner ve uyarı verir.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import rarfile  # type: ignore
        try:
            with rarfile.RarFile(str(rar_path)) as rf:
                rf.extractall(str(out_dir))
                return sum(1 for _ in out_dir.rglob("*") if _.is_file())
        except rarfile.BadRarFile:
            pass
        except rarfile.RarCannotExec:
            pass
    except ImportError:
        pass

    try:
        import patoolib  # type: ignore
        patoolib.extract_archive(str(rar_path), outdir=str(out_dir), verbosity=-1)
        return sum(1 for _ in out_dir.rglob("*") if _.is_file())
    except (ImportError, Exception):
        pass

    import subprocess
    for exe in ["7z", "7z.exe", r"C:\Program Files\7-Zip\7z.exe",
                r"C:\Program Files (x86)\7-Zip\7z.exe"]:
        try:
            result = subprocess.run(
                [exe, "x", "-y", f"-o{out_dir}", str(rar_path)],
                capture_output=True, timeout=300,
            )
            if result.returncode == 0:
                return sum(1 for _ in out_dir.rglob("*") if _.is_file())
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    print(f"  [HATA] RAR extract edilemedi: {rar_path.name}")
    print(f"         Çözüm: pip install rarfile  + unrar.exe PATH'de olmalı")
    print(f"         Alternatif: pip install patool   (otomatik tool detect)")
    print(f"         Veya: 7-Zip kurup PATH'e ekle  (https://www.7-zip.org/)")
    return 0


def download_url(url: str, dst: Path, chunk_size: int = 8 * 1024 * 1024) -> int:
    """Bir URL'den dosya indir, progress göster."""
    import urllib.request
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0:
        print(f"  [INFO] Önbellekte: {dst.name} ({dst.stat().st_size / (1024*1024):.1f} MB)")
        return dst.stat().st_size

    req = urllib.request.Request(url, headers={"User-Agent": "CiftciApp-ML/1.0"})
    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        tmp = dst.with_suffix(dst.suffix + ".part")
        with open(tmp, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded * 100 / total
                    print(f"\r  [DL] {dst.name}: {downloaded/(1024*1024):.1f}/{total/(1024*1024):.1f} MB ({pct:.1f}%)",
                          end="", flush=True)
                else:
                    print(f"\r  [DL] {dst.name}: {downloaded/(1024*1024):.1f} MB", end="", flush=True)
        tmp.rename(dst)
    print()
    return downloaded


def merge_into_raw(
    source: str,
    source_class: str,
    unified_class: str,
    images: Iterable[Path],
    raw_dir: Path = DEFAULT_RAW_DIR,
    validate: bool = True,
    max_count: Optional[int] = None,
) -> Tuple[int, int]:
    """Görselleri birleşik raw/<unified_class>/ altına kopyala.

    Returns:
        (written, skipped_invalid)
    """
    dst_dir = raw_dir / safe_dirname(unified_class)
    dst_dir.mkdir(parents=True, exist_ok=True)
    written, skipped = 0, 0
    count = 0
    for src in images:
        if max_count is not None and count >= max_count:
            break
        unified_name = make_unified_id(source, src.name, count)
        dst = dst_dir / unified_name
        if dst.exists():
            count += 1
            continue
        ok = copy_image(src, dst, validate=validate)
        if ok:
            written += 1
        else:
            skipped += 1
        count += 1
    return written, skipped


def print_step(title: str, char: str = "=") -> None:
    print()
    print(char * 70)
    print(f"  {title}")
    print(char * 70)
