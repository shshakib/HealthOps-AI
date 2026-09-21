FROM node:24-bookworm-slim@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553 AS dashboard
WORKDIR /workspace/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src/ ./src/
RUN npm run build

# python:3.11-slim-bookworm, resolved 2026-09-13.
FROM python:3.11-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HEALTHOPS_DB_PATH=/data/healthops.sqlite3

WORKDIR /app
COPY pyproject.toml README.md requirements-dev.lock requirements-observability.lock ./
COPY src/ ./src/
COPY --from=dashboard /workspace/src/healthops/static/ ./src/healthops/static/
COPY data/clinicaltrials/ /app/data/clinicaltrials/
RUN pip install --no-cache-dir -c requirements-observability.lock ".[observability]" \
    && groupadd --gid 10001 healthops \
    && useradd --uid 10001 --gid healthops --no-create-home healthops \
    && mkdir -p /data \
    && chown healthops:healthops /data

COPY scripts/demo.py /app/scripts/demo.py
COPY scripts/check_stack.py /app/scripts/check_stack.py
COPY scripts/check_persistence.py /app/scripts/check_persistence.py
USER 10001:10001
ENV HEALTHOPS_TRIAL_DIR=/app/data/clinicaltrials
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).close()"]

CMD ["python", "-m", "uvicorn", "healthops.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
