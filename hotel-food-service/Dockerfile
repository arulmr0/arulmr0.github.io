FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY pyproject.toml ./
COPY app ./app
COPY web ./web
RUN pip install --no-cache-dir . && adduser --disabled-password --gecos "" hfs \
    && mkdir -p /data && chown hfs /data
USER hfs
ENV HFS_DATABASE_URL=sqlite:////data/hfs.db
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
