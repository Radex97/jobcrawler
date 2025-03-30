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

# Kopiere Backend
COPY backend ./backend

# Erstelle statischen Ordner
RUN mkdir -p ./backend/static

# Kopiere Frontend-Build aus der Build-Phase
COPY --from=frontend-build /app/frontend-build/ ./backend/static/

# Installiere Abhängigkeiten
RUN pip install -r backend/requirements.txt gunicorn psycopg2-binary

# Debug: Inhalt des statischen Ordners anzeigen
RUN ls -la ./backend/static/

# Stelle sicher, dass der statische Ordner vorhanden ist und lesbare Berechtigungen hat
RUN chmod -R 755 ./backend/static

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Exponiere den Port
EXPOSE 8080

# Füge Healthcheck hinzu - mit kurzem Timeout
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Starte die Anwendung mit Debug-Ausgabe - kürzeres Timeout für bessere Antwortzeiten
CMD cd backend && python -m gunicorn.app.wsgiapp --bind 0.0.0.0:${PORT} --log-level debug --access-logfile - --error-logfile - --timeout 30 --workers 2 src.app:app 