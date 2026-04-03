"""
Async SQLAlchemy veritabanı motoru ve oturum yönetimi.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import logger


# --- Async Engine ---
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

# --- Session Factory ---
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# --- Base Model ---
class Base(DeclarativeBase):
    """Tüm SQLAlchemy modelleri bu sınıftan türetilir."""
    pass


# --- Dependency Injection ---
async def get_db():
    """FastAPI Depends() ile kullanılacak async DB oturumu."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Uygulama başlatıldığında DB bağlantısını test eder."""
    try:
        async with engine.begin() as conn:
            # Basit bağlantı testi
            await conn.run_sync(lambda sync_conn: None)
        logger.info("✅ Veritabanı bağlantısı başarılı")
    except Exception as e:
        logger.error(f"❌ Veritabanı bağlantı hatası: {e}")
        raise
