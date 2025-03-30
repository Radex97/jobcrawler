# Build-Phase für das Frontend
FROM node:14-slim AS frontend-build
WORKDIR /app
COPY frontend ./frontend
# Debug angular.json
RUN cat frontend/angular.json | grep outputPath -A 2
# Angular Build durchführen
RUN cd frontend && npm install && npm install --save-dev @types/node && npm run build
# Debug: Inhalt des Build-Verzeichnisses anzeigen
RUN ls -la frontend/dist

# Runtime-Phase
FROM python:3.9-slim
WORKDIR /app

# Kopiere Backend
COPY backend ./backend

# Erstelle statischen Ordner
RUN mkdir -p ./backend/static

# Kopiere Frontend-Build aus der Build-Phase
COPY --from=frontend-build /app/frontend/dist/frontend/ ./backend/static/

# Installiere Abhängigkeiten
RUN pip install -r backend/requirements.txt

# Debug: Inhalt des statischen Ordners anzeigen
RUN ls -la ./backend/static/

# Stelle sicher, dass der statische Ordner vorhanden ist und lesbare Berechtigungen hat
RUN chmod -R 755 ./backend/static

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Exponiere den Port
EXPOSE 8080

# Starte die Anwendung mit Debug-Ausgabe
CMD cd backend && gunicorn --bind 0.0.0.0:${PORT} --log-level debug --access-logfile - --error-logfile - src.app:app 