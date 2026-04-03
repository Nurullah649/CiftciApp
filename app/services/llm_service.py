"""
LLM Servisi: Model yükleme, inference ve streaming.
llama-cpp-python kullanarak yerel GGUF model ile çıkarım yapar.
"""

import time
import psutil
from typing import Generator, Optional
from llama_cpp import Llama, LlamaRAMCache

from app.core.config import settings
from app.core.logging import logger


class LLMService:
    """Yerel LLM model yönetimi."""

    def __init__(self):
        self.llm: Optional[Llama] = None
        self.model_loaded = False

    def load_model(self):
        """Modeli belleğe yükler. Lifespan event'te çağrılır."""
        try:
            logger.info(f"🔄 Model yükleniyor: {settings.MODEL_FILENAME}")
            start_ram = self.get_ram_usage()

            self.llm = Llama(
                model_path=settings.MODEL_PATH,
                n_ctx=2048,
                n_threads=4,  # 4 çekirdekle sınırlandırıldı (sunucu darboğazını önlemek için)
                n_batch=128,  # CPU prompt işleme yükü azaltıldı
                n_gpu_layers=0,  # CPU-only
                use_mlock=True,  # Model RAM'de kilitlenir, swap engellenir
                verbose=False,
            )

            # Prompt cache — system prompt her istekte yeniden işlenmez
            self.llm.set_cache(LlamaRAMCache(capacity_bytes=2 * (1 << 30)))  # 2GB
            logger.info("💾 Prompt cache aktif (LlamaRAMCache, 2GB)")

            end_ram = self.get_ram_usage()
            logger.info(f"✅ Model yüklendi! RAM: {end_ram:.0f} MB (+{end_ram - start_ram:.0f} MB)")

            # Model pre-warming — ilk istek gecikmesini önler
            logger.info("🔥 Model ısıtılıyor (pre-warm)...")
            warmup_start = time.time()
            self.llm("Merhaba", max_tokens=1)
            logger.info(f"🔥 Model ısıtıldı ({time.time() - warmup_start:.1f}s)")

            self.model_loaded = True

        except Exception as e:
            logger.error(f"❌ Model yüklenemedi: {e}")
            self.llm = None
            self.model_loaded = False

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        """Senkron LLM inference. Tam yanıtı string olarak döndürür."""
        if not self.llm:
            raise RuntimeError("AI modeli yüklü değil")

        start_time = time.time()
        start_ram = self.get_ram_usage()
        logger.info("🧠 Model düşünüyor...")

        output = self.llm(
            prompt,
            max_tokens=max_tokens,
            stop=["<|im_end|>"],
            echo=False,
            temperature=0.3,
        )

        response = output["choices"][0]["text"].strip()

        duration = time.time() - start_time
        end_ram = self.get_ram_usage()
        logger.info(f"✅ Cevap üretildi ({duration:.2f}s, RAM: {end_ram:.0f} MB, Δ{end_ram - start_ram:+.0f} MB)")

        return response

    def stream_generate(self, prompt: str, max_tokens: int = 2048) -> Generator[str, None, None]:
        """Streaming LLM inference. Token-by-token yield eder."""
        if not self.llm:
            raise RuntimeError("AI modeli yüklü değil")

        logger.info("🧠 Model düşünüyor (streaming)...")

        for chunk in self.llm(
            prompt,
            max_tokens=max_tokens,
            stop=["<|im_end|>"],
            echo=False,
            temperature=0.3,
            stream=True,
        ):
            token = chunk["choices"][0]["text"]
            if token:
                yield token

    @staticmethod
    def get_ram_usage() -> float:
        """Anlık RAM kullanımını MB cinsinden döndürür."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def build_prompt(
        self,
        question: str,
        context_data: str,
        history_str: str,
        current_date_str: str,
    ) -> str:
        """ChatML formatında tam prompt oluşturur (kompakt versiyon)."""
        system_prompt = f"""Sen Çiftçi AI'sın — deneyimli bir Ziraat Mühendisi. Pratik, net ve uygulanabilir tarımsal tavsiyeler ver.

BAĞLAM: {context_data}

KURALLAR:
- Sadece bitkisel üretim, toprak, sulama, gübreleme, zirai mücadele konularında cevap ver.
- Konu dışı sorularda: "Ben uzman bir ziraat asistanıyım. Sadece tarımsal konularda yardımcı olabilirim."
- Geçmiş sohbet sadece bağlamdır; yeni konuda eski cevapları tekrarlama.
- İstenmeden uzun plan/takvim oluşturma, doğrudan cevapla.
- Zirai ilaç önerirken **koruyucu ekipman** ve **hasat öncesi bekleme süresi** uyarısı ekle.
- Birimlerle cevapla (ör: Dekara 15kg). Hava yağmurluysa sulama önerisini güncelle.

PLAN İSTENİRSE: 1)Toprak Hazırlık 2)Ekim 3)Bakım/Besleme 4)Hasat şeklinde yapılandır.

FORMAT: Türkçe, Markdown. Bir EYLEM öneriyorsan sona ekle:
[GÖREV: <Eylem> | <Açıklama> | YYYY-MM-DD HH:MM]
Tarih bugünden ({current_date_str}) sonra, sabah erken veya akşam serinliğine ayarla."""

        full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        full_prompt += history_str
        full_prompt += f"<|im_start|>user\n/no_think\n{question}<|im_end|>\n<|im_start|>assistant\n"

        return full_prompt


# Singleton instance
llm_service = LLMService()
