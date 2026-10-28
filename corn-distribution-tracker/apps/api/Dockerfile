# syntax=docker/dockerfile:1
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

# Unprivileged runtime user with a fixed numeric id (no host name resolution).
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py ./
COPY config ./config
COPY corn ./corn
COPY --chown=app:app bin ./bin

# Local-mode evidence storage (STORAGE_MODE=local) must be writable by the app user.
RUN mkdir -p /app/storage-data && chown -R app:app /app/storage-data \
    && chmod +x bin/*.sh

USER 10001:10001
EXPOSE 8000

# Liveness only; readiness (/health/ready) also probes DB + storage.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health/live', timeout=3)"

CMD ["sh", "bin/start.sh"]
