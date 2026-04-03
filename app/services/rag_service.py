"""
RAG Servisi: Qdrant vektör veritabanı ile bilgi çekme (Retrieval-Augmented Generation).
"""

import time
import hashlib
from typing import Optional
from functools import lru_cache

import ollama
from qdrant_client import QdrantClient

from app.core.config import settings
from app.core.logging import logger


class RAGService:
    """Qdrant + Ollama embedding ile RAG context çekme."""

    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.connected = False

    def connect(self):
        """Qdrant'a bağlanır. Lifespan event'te çağrılır."""
        try:
            self.client = QdrantClient(url=settings.QDRANT_URL)
            logger.info(f"✅ Qdrant bağlantısı başarılı: {settings.QDRANT_URL}")
            self.connected = True
        except Exception as e:
            logger.error(f"❌ Qdrant bağlantı hatası: {e}")
            self.client = None
            self.connected = False

    @staticmethod
    @lru_cache(maxsize=128)
    def _cached_embed(text_hash: str, text: str) -> tuple:
        """
        Cache'li embedding hesaplama.
        Aynı sorgu tekrar gönderildiğinde Ollama API çağrılmaz.
        text_hash parametresi cache key olarak kullanılır.
        """
        embed_start = time.time()
        response = ollama.embed(
            model=settings.OLLAMA_EMBED_MODEL,
            input=text,
        )
        duration = time.time() - embed_start
        logger.info(f"🔢 Embedding hesaplandı ({duration:.2f}s) [CACHE MISS]")
        return tuple(response["embeddings"][0])

    def get_context(self, enriched_query: str) -> str:
        """
        Verilen sorguyu embedding'e çevirip Qdrant'ta arar.
        Benzerlik skoru 0.4'ün üzerindeki sonuçları context olarak döndürür.
        """
        if not self.client:
            logger.warning("Qdrant bağlantısı yok, RAG context boş döndürülüyor")
            return ""

        try:
            total_start = time.time()

            # Sorguyu embedding'e çevir (cache'li)
            text_hash = hashlib.md5(enriched_query.encode()).hexdigest()
            query_vector = list(self._cached_embed(text_hash, enriched_query))

            # Qdrant'ta ara
            search_start = time.time()
            results = self.client.search(
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=query_vector,
                limit=3,
                score_threshold=0.4,
            )
            search_duration = time.time() - search_start

            if not results:
                logger.debug("RAG: Eşleşme bulunamadı")
                return ""

            # Sonuçları birleştir
            context_parts = []
            for hit in results:
                text = hit.payload.get("text", "")
                score = hit.score
                context_parts.append(f"[Skor: {score:.2f}] {text}")
                logger.debug(f"RAG hit: score={score:.2f}, text={text[:80]}...")

            combined = "\n---\n".join(context_parts)
            total_duration = time.time() - total_start
            logger.info(
                f"RAG: {len(results)} sonuç bulundu "
                f"(toplam: {total_duration:.2f}s, arama: {search_duration:.2f}s)"
            )
            return combined

        except Exception as e:
            logger.error(f"RAG hatası: {e}")
            return ""


# Singleton instance
rag_service = RAGService()
