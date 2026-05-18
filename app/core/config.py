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

    # --- Veritabanı (PostgreSQL) ---
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "ciftci"
    DB_PASSWORD: str = ""
    DB_NAME: str = "tarim_db"

    # --- API Anahtarları ---
    WEATHER_API_KEY: str = ""
    GEOCODING_API_KEY: str = ""

    # --- Vektör Veritabanı ---
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "tarim_bilgi_bankasi"
    OLLAMA_EMBED_MODEL: str = "embeddinggemma"

    # --- Önbellek (Redis) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Model ---
    MODEL_FILENAME: str = "urfa_ciftci_ai_qwen3_4b_thinking.Q4_K_M.gguf"
    MODEL_DIR: str = "/app/models"  # Docker compose içinde bind edilen klasör

    # --- Uygulama ---
    SIMULATION_MODE: bool = True

    # --- Bitki hastalığı CNN (analyze-plant) ---
    # Boş bırakılırsa proje kökünde ml/checkpoints/best.pt ve ml/*.json kullanılır.
    PLANT_CHECKPOINT_PATH: Optional[str] = None
    PLANT_LABELS_PATH: Optional[str] = None
    PLANT_TREATMENT_PATH: Optional[str] = None

    # --- BKÜ (Tarım Bakanlığı bitki koruma / MRL canlı tablo) ---
    BKU_BASE_URL: str = "https://bku.tarimorman.gov.tr"
    BKU_TIMEOUT_SECONDS: float = 25.0
    BKU_MAX_ROWS_PER_SUBSTANCE: int = 60
    BKU_MRL_MAP_PATH: Optional[str] = None  # boşsa proje/ml/bku_mrl_active_map.json

    @property
    def DATABASE_URL(self) -> str:
        """Async SQLAlchemy bağlantı URL'si (asyncpg)."""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Alembic / senkron işlemler için bağlantı URL'si (psycopg2)."""
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def MODEL_PATH(self) -> str:
        """GGUF model dosyasının tam yolu."""
        # MODEL_DIR dışarıdan (env) verilmişse onu kullan,
        # aksi halde proje köküne bak (lokal geliştirme için).
        if os.path.isdir(self.MODEL_DIR):
            return os.path.join(self.MODEL_DIR, self.MODEL_FILENAME)
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        return os.path.join(base_dir, self.MODEL_FILENAME)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
