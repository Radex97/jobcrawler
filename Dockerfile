# Build-Phase für das Frontend
FROM node:14-slim AS frontend-build
WORKDIR /app
COPY frontend ./frontend
# Debug angular.json
RUN cat frontend/angular.json | grep outputPath -A 2
# Angular Build durchführen
RUN cd frontend && npm install && npm install --save-dev @types/node && npm run build
# Debug: Inhalt des Build-Verzeichnisses anzeigen und Kopieren ins Zielverzeichnis
RUN ls -la frontend/dist && ls -la frontend/dist/frontend || true
# Kopiere Build-Dateien in ein einheitliches Verzeichnis für späteres Kopieren
RUN mkdir -p /app/frontend-build && \
    if [ -d frontend/dist/frontend ]; then \
        cp -r frontend/dist/frontend/* /app/frontend-build/; \
    elif [ -d frontend/dist ]; then \
        cp -r frontend/dist/* /app/frontend-build/; \
    else \
        echo "<html><body><h1>Jobbig Job Crawler</h1><p>The API is available at /api/</p><p>Info: Frontend-Build ist fehlgeschlagen.</p></body></html>" > /app/frontend-build/index.html; \
    fi

# Runtime-Phase
FROM python:3.9-slim
WORKDIR /app

# Installiere Abhängigkeiten für psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Kopiere Anforderungen zuerst für besseres Caching
COPY backend/requirements.txt .

# Installiere Python-Abhängigkeiten 
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir psycopg2-binary psycopg2 psycopg && \
    pip install --no-cache-dir gunicorn

# Kopiere Backend-Code
COPY backend/ .

# Kopiere Frontend-Build in den statischen Ordner
COPY frontend/dist/ static/

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Exponiere den Port
EXPOSE 8080

# Füge Healthcheck hinzu - mit kurzem Timeout
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Starte die Anwendung
CMD ["gunicorn", "src.app:app", "--bind", "0.0.0.0:$PORT"] 