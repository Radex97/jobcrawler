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
COPY --from=frontend-build /app/frontend/dist ./backend/static

# Installiere Abhängigkeiten
RUN pip install -r backend/requirements.txt

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1

# Starte die Anwendung
CMD cd backend && gunicorn src.app:app 