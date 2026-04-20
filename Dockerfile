###############################################################################
# Çiftçi AI — Backend Dockerfile
# llama-cpp-python C++ derlemesi gerektirdiği için multi-stage kullanıyoruz.
###############################################################################

# ---------- 1. AŞAMA: Builder (C++ derleme ortamı) -------------------------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"

# llama-cpp-python + psycopg2 için sistem kütüphaneleri
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        curl \
        libopenblas-dev \
        libpq-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip wheel setuptools \
 && /opt/venv/bin/pip install -r requirements.txt


# ---------- 2. AŞAMA: Runtime (ince imaj) ----------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    TZ=Europe/Istanbul

# Çalışma zamanı için gerekli sistem paketleri (OpenBLAS + libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libopenblas0 \
        libpq5 \
        tzdata \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Virtualenv'i builder'dan kopyala
COPY --from=builder /opt/venv /opt/venv

# Non-root kullanıcı (güvenlik)
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Uygulama kodunu kopyala
COPY --chown=appuser:appuser app ./app
# GGUF modeli için klasör (compose volume ile mount edilir)
RUN mkdir -p /app/models /app/logs && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
