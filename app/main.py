"""
Çiftçi AI API — Ana Uygulama
FastAPI uygulamasını yapılandırır, router'ları bağlar ve lifespan event'lerini yönetir.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import logger
from app.core.config import settings
from app.core.database import init_db
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.notification_service import notification_service
from app.core.redis import redis_client

# Router'lar
from app.routers import auth, chat, tasks, tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Uygulama yaşam döngüsü.
    Startup: DB bağlantısı, model yükleme, Qdrant bağlantısı, scheduler başlatma.
    Shutdown: Kaynakları temizleme.
    """
    logger.info("🚀 Çiftçi AI API başlatılıyor...")

    # Startup
    await init_db()
    llm_service.load_model()
    rag_service.connect()
    notification_service.start_scheduler()
    await redis_client.connect()

    logger.info("✅ Tüm servisler hazır!")
    logger.info(f"📍 Simülasyon modu: {'AÇIK' if settings.SIMULATION_MODE else 'KAPALI'}")

    yield

    # Shutdown
    logger.info("🛑 Çiftçi AI API kapatılıyor...")
    notification_service.stop_scheduler()
    await redis_client.disconnect()


# --- FastAPI App ---
app = FastAPI(
    title="Çiftçi AI API",
    description="Yapay zeka destekli tarımsal danışmanlık sistemi",
    version="2.0.0",
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Prodüksiyon'da mobil app origin'i ile sınırlandırılmalı
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Router'ları Bağla ---
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(tasks.router)
app.include_router(tools.router)


@app.get("/")
async def root():
    """API kök endpoint'i."""
    return {
        "name": "Çiftçi AI API",
        "version": "2.0.0",
        "docs": "/docs",
    }


# --- Doğrudan Çalıştırma ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
