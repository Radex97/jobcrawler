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

# Optimierte Installation der Abhängigkeiten in separaten Schritten
# und Kombiniere die apt-get Befehle, um die Anzahl der Schichten zu reduzieren
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Kopiere Anforderungen zuerst für besseres Caching
COPY backend/requirements.txt .

# Installiere Python-Abhängigkeiten in separaten Schritten, um Speicher zu sparen
RUN pip install --no-cache-dir gunicorn
RUN pip install --no-cache-dir psycopg2-binary 
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere Backend-Code
COPY backend/ .

# Kopiere Frontend-Build in den statischen Ordner
COPY frontend/dist/ static/

# Erstelle statisches Verzeichnis
RUN mkdir -p static

# Fallback Indexseite, falls kein Frontend vorhanden ist
RUN echo "<html><body><h1>Jobbig Job Crawler</h1><p>API is running at /api/</p></body></html>" > static/index.html

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Exponiere den Port
EXPOSE 8080

# Füge Healthcheck hinzu
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Starte die Anwendung mit reduzierten Workers
CMD gunicorn src.app:app --bind 0.0.0.0:$PORT --log-level info --timeout 30 --workers 1 