# One container: FastAPI backend + the exported PWA. Fits a free Render/Railway instance.

# ---- 1. build the static frontend
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# same-origin API: leave NEXT_PUBLIC_API_URL empty
RUN npm run build

# ---- 2. Python runtime with Tesseract (English, Tamil, Hindi)
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-eng tesseract-ocr-tam tesseract-ocr-hin \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY schemes/ schemes/
COPY --from=web /web/out frontend/out
RUN useradd -m sathi && chown -R sathi /app
USER sathi
WORKDIR /app/backend
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",\"8000\")}/api/v1/health')"
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
