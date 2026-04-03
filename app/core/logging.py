"""
Loguru tabanlı profesyonel logging yapılandırması.
Tüm print() çağrılarını değiştirir.
"""

import sys
from loguru import logger

# Varsayılan handler'ı kaldır
logger.remove()

# Konsol çıktısı (renkli)
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | {message}",
    colorize=True,
)

# Dosya çıktısı (döngülü, 10MB'da yeni dosya, 7 gün saklama)
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    encoding="utf-8",
)

# Bu modülü import eden her dosya doğrudan logger'ı kullanabilir
__all__ = ["logger"]
