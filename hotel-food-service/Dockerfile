FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY pyproject.toml ./
COPY app ./app
COPY web ./web
RUN pip install --no-cache-dir . \
    && adduser --disabled-password --gecos "" --uid 1000 hfs \
    && mkdir -p /data && chown hfs /data
USER hfs
# PORT is injected by most hosts (Render, Railway, Fly); Hugging Face reads app_port.
ENV HFS_DATABASE_URL=sqlite:////data/hfs.db PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import os,urllib.request;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health')"
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
