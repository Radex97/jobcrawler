# Build-Phase für das Frontend
FROM node:14-slim AS frontend-build
WORKDIR /app
COPY frontend ./frontend
RUN cd frontend && npm install && npm install --save-dev @types/node && npm run build

# Runtime-Phase
FROM python:3.9-slim
WORKDIR /app

# Kopiere Backend
COPY backend ./backend

# Erstelle statischen Ordner und erstelle eine leere Index-Datei
RUN mkdir -p ./backend/static && \
    echo "<html><body><h1>Jobbig Job Crawler</h1><p>The API is available at /api/</p></body></html>" > ./backend/static/index.html

# Installiere Abhängigkeiten
RUN pip install -r backend/requirements.txt

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Exponiere den Port
EXPOSE 8080

# Starte die Anwendung
CMD cd backend && gunicorn --bind 0.0.0.0:${PORT} src.app:app 