"""
Merkezi konfigürasyon modülü.
Tüm ortam değişkenleri burada tanımlanır ve .env dosyasından okunur.
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Uygulama ayarları — .env dosyasından otomatik yüklenir."""

    # --- Güvenlik ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 hafta

    # --- Veritabanı ---
    DB_HOST: str = "localhost"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "tarim_db"

    # --- API Anahtarları ---
    WEATHER_API_KEY: str = ""
    GEOCODING_API_KEY: str = ""
    PLANT_ID_API_KEY: str = ""

    # --- Vektör Veritabanı ---
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "tarim_bilgi_bankasi"
    OLLAMA_EMBED_MODEL: str = "embeddinggemma"

    # --- Önbellek (Redis) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Model ---
    MODEL_FILENAME: str = "urfa_ciftci_ai_qwen3_4b_thinking.Q4_K_M.gguf"

    # --- Uygulama ---
    SIMULATION_MODE: bool = True

    @property
    def DATABASE_URL(self) -> str:
        """Async SQLAlchemy bağlantı URL'si."""
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}/{self.DB_NAME}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Alembic için senkron bağlantı URL'si."""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}/{self.DB_NAME}"

    @property
    def MODEL_PATH(self) -> str:
        """GGUF model dosyasının tam yolu."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, self.MODEL_FILENAME)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
