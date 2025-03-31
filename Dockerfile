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

# Installiere Chrome, ChromeDriver und andere Abhängigkeiten
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    gnupg2 && \
    # Chrome installieren
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    # Aufräumen
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Manuelle Installation einer kompatiblen ChromeDriver-Version für moderne Chrome-Versionen
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    echo "Gefundene Chrome-Version: ${CHROME_VERSION}" && \
    # Verwende die neueste stabile ChromeDriver-Version (für Chrome 114+)
    wget -q "https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.94/linux64/chromedriver-linux64.zip" && \
    unzip -q chromedriver-linux64.zip && \
    mv chromedriver-linux64/chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf chromedriver-linux64.zip chromedriver-linux64 && \
    echo "ChromeDriver installiert: $(chromedriver --version)"

# Kopiere Anforderungen zuerst für besseres Caching
COPY backend/requirements.txt .

# Installiere Python-Abhängigkeiten in separaten Schritten, um Speicher zu sparen
RUN pip install --no-cache-dir gunicorn
RUN pip install --no-cache-dir psycopg2-binary 
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere Backend-Code
COPY backend/ .

# Erstelle statisches Verzeichnis mit einer Fallback-Indexseite und CSS
RUN mkdir -p static && \
    echo "<html><head><title>Jobbig Job Crawler</title><link rel=\"stylesheet\" href=\"styles.css\"></head><body><div class=\"container\"><h1>Jobbig Job Crawler</h1><p>Die API ist unter /api/ verfügbar</p><ul><li><a href=\"/api/status\">API Status</a></li><li><a href=\"/diagnostics\">Diagnose</a></li></ul></div></body></html>" > static/index.html && \
    echo "body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; } .container { max-width: 800px; margin: 50px auto; padding: 20px; background-color: white; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); } h1 { color: #333; } a { color: #0066cc; }" > static/styles.css

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV DISPLAY=:99

# Exponiere den Port
EXPOSE 8080

# Füge Healthcheck hinzu
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Starte X virtual framebuffer und die Anwendung
CMD Xvfb :99 -screen 0 1280x1024x24 -ac +extension GLX +render -noreset & \
    gunicorn src.app:app --bind 0.0.0.0:$PORT --log-level info --timeout 30 --workers 1 