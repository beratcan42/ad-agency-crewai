# =================================================================
# Agency API + Workers - Single-stage build
# =================================================================
# NOT: Multi-stage --prefix=/install transitive dep'leri kaybetti
# (packaging vs.). Single-stage daha buyuk ama guvenilir.
# =================================================================

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    TZ=Europe/Istanbul

# Sistem bagimliliklari (psycopg + tini + curl debugging)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libpq5 \
        curl \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 -s /bin/bash agency

WORKDIR /app

# Bagimliliklari pyproject.toml'dan kur
COPY pyproject.toml ./
RUN mkdir -p src && touch src/__init__.py
RUN pip install --upgrade pip wheel setuptools \
 && pip install -e .

# Build-time bagimliliklari kaldir (image kucult)
RUN apt-get update && apt-get purge -y --auto-remove build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Uygulama kodu (bind mount dev'de override eder)
COPY --chown=agency:agency src ./src

USER agency

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-3} --timeout-keep-alive 30 --log-level info"]
