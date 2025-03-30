from .models import Job, db, connect_db, refresh_db, serialize_job
from flask import Flask, cli, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import logging
import glob
import time
import functools
import socket
import sys
from .scraping import find_monster_jobs, find_stepstone_jobs
from datetime import datetime

# Prozess-Startzeit für Uptime-Berechnungen
process_start_time = time.time()

# Logging konfigurieren - reduziertes Logging-Level für Produktion
log_level = logging.INFO
if os.environ.get("DEBUG") == "1":
    log_level = logging.DEBUG

logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Weniger häufig verwendete Module nur bei Bedarf importieren
def lazy_import(module_name):
    try:
        return __import__(module_name)
    except ImportError as e:
        logger.warning(f"Modul {module_name} konnte nicht importiert werden: {e}")
        return None

# Bedingte Importe für Datenbankfunktionalität - darf nicht fehlschlagen für Healthcheck
try:
    # Erstmal versuchen, die benötigten Module zu installieren, falls sie fehlen
    try:
        import subprocess
        logger.info("Versuche, fehlende Datenbankmodule zu installieren...")
        
        # Liste der zu installierenden Module
        db_modules = ["psycopg2-binary", "psycopg", "psycopg2", "python-dotenv"]
        for module in db_modules:
            try:
                subprocess.check_call(["pip", "install", module, "--no-cache-dir"])
                logger.info(f"Modul {module} erfolgreich installiert")
            except Exception as e:
                logger.warning(f"Konnte Modul {module} nicht installieren: {e}")
    except Exception as e:
        logger.warning(f"Konnte zusätzliche Module nicht installieren: {e}")
        
    # Jetzt versuchen, die Module zu importieren
    import psycopg
    from .database import get_database, save_new_jobs, get_jobs_by_criteria, verify_database_connection, create_tables_if_not_exist
    db_imports_successful = True
    logger.info("Datenbankmodule erfolgreich importiert")
except ImportError as e:
    db_imports_successful = False
    logger.warning(f"Datenbankmodule konnten nicht importiert werden: {e}")
    
    # Dummy-Funktionen für den Fall, dass die Importe fehlschlagen
    def verify_database_connection():
        return False
        
    def save_new_jobs(jobs):
        logger.warning("Keine Datenbankunterstützung verfügbar, Jobs werden nicht gespeichert")
        return
        
    def get_jobs_by_criteria(*args, **kwargs):
        logger.warning("Keine Datenbankunterstützung verfügbar, keine Jobs abgerufen")
        return []
        
    def create_tables_if_not_exist():
        logger.warning("Keine Datenbankunterstützung verfügbar, Tabellen können nicht erstellt werden")
        return False

# Den absoluten Pfad zum aktuellen Modul finden
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, 'static')

# Falls das static-Verzeichnis nicht existiert, verwenden wir den Pfad relativ zum aktuellen Verzeichnis
if not os.path.exists(static_dir):
    base_dir = os.path.dirname(current_dir)
    static_dir = os.path.join(base_dir, 'static')
    logger.info(f"Static folder not found at module level, using parent directory: {static_dir}")

# Wenn immer noch nicht gefunden, nehmen wir einen absoluten Pfad
if not os.path.exists(static_dir):
    static_dir = '/app/backend/static'
    logger.info(f"Static folder still not found, using absolute path: {static_dir}")

# Funktion zur Erfassung von System-Informationen
def get_system_info():
    """Sammelt System-Informationen für Diagnose-Zwecke"""
    info = {
        "os": sys.platform,
        "python_version": sys.version,
        "environment": os.environ.get("RAILWAY_ENVIRONMENT", "unbekannt"),
        "hostname": socket.gethostname()
    }
    
    # Prüfe auf bestimmte Umgebungen
    if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
        info["environment"] = "railway"
        info["domain"] = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    elif os.environ.get("HEROKU_APP_NAME"):
        info["environment"] = "heroku"
    
    # Speichernutzung (wenn psutil verfügbar ist)
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        info["memory"] = {
            "rss_mb": round(memory_info.rss / (1024 * 1024), 2),
            "vms_mb": round(memory_info.vms / (1024 * 1024), 2),
            "percent": process.memory_percent()
        }
    except ImportError:
        # Wenn psutil nicht verfügbar ist, versuche einige grundlegende Informationen
        import resource
        try:
            rusage = resource.getrusage(resource.RUSAGE_SELF)
            info["memory"] = {
                "max_rss_kb": rusage.ru_maxrss,
                "shared_kb": rusage.ru_ixrss,
                "unshared_kb": rusage.ru_idrss
            }
        except Exception as e:
            logger.warning(f"Konnte keine Speichernutzung erfassen: {e}")
    
    return info

# Funktion zum Erstellen der Flask-App
def create_app():
    """Erstellt und konfiguriert die Flask-App"""
    # creating the Flask application
    app = Flask(__name__, static_folder=static_dir, static_url_path='')
    
    # activate CORS for flask app
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Log wichtige Startup-Informationen
    logger.info(f"Flask-App wird mit Python {sys.version} auf {sys.platform} gestartet")
    logger.info(f"Arbeitsverzeichnis: {os.getcwd()}")
    logger.info(f"Railway-Umgebungsvariablen: {[k for k in os.environ.keys() if k.startswith('RAILWAY')]}")
    
    # load .env variables
    try:
        cli.load_dotenv(".env")
    except Exception as e:
        logger.info(f"Keine .env Datei gefunden oder Fehler beim Laden: {e}")

    # get DB_URI from environ variable (useful for production/testing) or,
    # if not set there, use development local db.
    database_url = os.environ.get("DATABASE_URL", "postgres:///jobbig")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ECHO"] = False
    app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secret123")

    # Flag, das angibt, ob die Datenbank verfügbar ist
    db_available = False

    try:
        # Versuche mehrmals, die Datenbankverbindung herzustellen
        for attempt in range(3):
            try:
                logger.info(f"Versuche Datenbankverbindung herzustellen (Versuch {attempt+1}/3)...")
                connect_db(app)
                # Prüfe, ob die Datenbank tatsächlich verbunden ist
                if db_imports_successful and verify_database_connection():
                    db.create_all()
                    logger.info("Datenbank erfolgreich verbunden und Tabellen erstellt")
                    db_available = True
                    break
                else:
                    logger.warning("Verbindung zur Datenbank konnte nicht verifiziert werden")
                    if attempt < 2:
                        logger.info("Warte 3 Sekunden vor dem nächsten Versuch...")
                        time.sleep(3)
            except Exception as e:
                logger.error(f"Fehler bei Datenbankverbindungsversuch {attempt+1}: {type(e).__name__}: {e}")
                if attempt < 2:
                    logger.info("Warte 3 Sekunden vor dem nächsten Versuch...")
                    time.sleep(3)
        
        if not db_available:
            logger.error("Datenbankverbindung konnte nach mehreren Versuchen nicht hergestellt werden")
            logger.warning("Anwendung läuft im eingeschränkten Modus ohne Datenbankfunktionalität")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei der Datenbankinitialisierung: {type(e).__name__}: {e}")
        logger.warning("Anwendung läuft im eingeschränkten Modus ohne Datenbankfunktionalität")
        # Nicht abbrechen, damit der Healthcheck trotzdem funktioniert

    # Überprüfung des statischen Ordners
    try:
        logger.info(f"Static folder path: {app.static_folder}")
        
        # Prüfen, ob der statische Ordner existiert
        if os.path.exists(app.static_folder):
            files = os.listdir(app.static_folder)
            logger.info(f"Static folder exists with {len(files)} files: {files[:10]}")
            
            # Überprüfen, ob index.html existiert
            if 'index.html' not in files:
                logger.warning("index.html not found in static folder")
                create_fallback_index(app)
        else:
            logger.warning(f"Static folder does not exist: {app.static_folder}")
            create_fallback_index(app)
            
        # Suche auch nach anderen möglichen statischen Verzeichnissen
        possible_static_dirs = glob.glob('/app/**/static', recursive=True)
        logger.info(f"Other possible static directories: {possible_static_dirs}")
    except Exception as e:
        logger.error(f"Error checking static folder: {e}")
    
    # WICHTIG: Der Healthcheck muss sofort reagieren - vor allen anderen Routen definieren
    @app.route("/health")
    def health_check():
        """Einfacher Health-Check-Endpunkt für Railway"""
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat()
        })
        
    @app.route("/")
    def index():
        """Hauptroute, die zum statischen Frontend weiterleitet"""
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route("/diagnostics")
    def diagnostics():
        """Diagnostik-Endpoint zur Fehlersuche"""
        # Versuche Verbindung zur Datenbank herzustellen
        db_connection_info = {
            "connected": False,
            "modules_available": db_imports_successful
        }
        
        # Teste Datenbankverbindung direkt
        try:
            start_time = time.time()
            db_connected = verify_database_connection()
            connection_duration = time.time() - start_time
            
            db_connection_info.update({
                "connected": db_connected,
                "connection_duration_seconds": round(connection_duration, 3),
                "environment_vars": {
                    "DATABASE_URL": "vorhanden" if os.environ.get("DATABASE_URL") else "nicht gesetzt",
                    "DATABASE_PUBLIC_URL": "vorhanden" if os.environ.get("DATABASE_PUBLIC_URL") else "nicht gesetzt",
                    "POSTGRES_URL": "vorhanden" if os.environ.get("POSTGRES_URL") else "nicht gesetzt",
                    "PGDATABASE": "vorhanden" if os.environ.get("PGDATABASE") else "nicht gesetzt"
                }
            })
            
            # Wenn verbunden, hole weitere Informationen
            if db_connected:
                conn = get_database()
                if conn:
                    with conn.cursor() as cur:
                        # PostgreSQL Version
                        cur.execute("SELECT version()")
                        pg_version = cur.fetchone()[0]
                        
                        # Verbindungsinformationen
                        cur.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port(), pg_backend_pid()")
                        db_info = cur.fetchone()
                        
                        # Aktuelle Transaktionen
                        cur.execute("SELECT count(*) FROM pg_stat_activity")
                        active_connections = cur.fetchone()[0]
                        
                        db_connection_info.update({
                            "postgres_version": pg_version,
                            "current_database": db_info[0],
                            "current_user": db_info[1],
                            "server_addr": str(db_info[2]),
                            "server_port": db_info[3],
                            "backend_pid": db_info[4],
                            "active_connections": active_connections
                        })
                    conn.close()
        except Exception as e:
            logger.error(f"Fehler bei der Diagnose-Datenbankverbindung: {type(e).__name__}: {e}")
            db_connection_info["error"] = f"{type(e).__name__}: {str(e)}"
        
        # Systeminfo mit mehr Details
        system_info = get_system_info()
        system_info.update({
            "python_version": sys.version,
            "platform": sys.platform,
            "hostname": socket.gethostname(),
            "process_id": os.getpid(),
            "railway_vars": {k: v[:20] + "..." if isinstance(v, str) and len(v) > 20 else v 
                          for k, v in os.environ.items() if k.startswith("RAILWAY_")}
        })
        
        return jsonify({
            "system_info": system_info,
            "database": db_connection_info,
            "static_files": {
                "path": app.static_folder,
                "exists": os.path.exists(app.static_folder),
                "files": os.listdir(app.static_folder) if os.path.exists(app.static_folder) else []
            },
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(time.time() - process_start_time)
        })
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        """Serve static files or the SPA"""
        logger.info(f"Request for path: {path}")
        
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            logger.info(f"Serving file directly: {path}")
            return send_from_directory(app.static_folder, path)
        else:
            try:
                logger.info(f"Serving index.html for path: {path}")
                return send_from_directory(app.static_folder, 'index.html')
            except Exception as e:
                logger.error(f"Error serving index.html: {e}")
                return "Jobbig API is running. (Error serving frontend)", 200
    
    # Timeout-Decorator für API-Routen
    def timeout_handler(timeout_seconds=15):  # Timeout von 5 auf 15 Sekunden erhöht
        """
        Ein Decorator, der die Ausführungszeit einer Funktion überwacht und 
        bei Überschreitung des Timeouts ein Beispielergebnis zurückgibt.
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                logger.info(f"Starte {func.__name__} mit Timeout von {timeout_seconds} Sekunden")
                
                try:
                    # Führe die Funktion aus
                    result = func(*args, **kwargs)
                    
                    # Prüfe, ob der Timeout überschritten wurde
                    elapsed_time = time.time() - start_time
                    if elapsed_time > timeout_seconds:
                        logger.warning(f"Timeout überschritten: {elapsed_time:.2f}s > {timeout_seconds}s")
                        # Fallback-Daten basierend auf der Route
                        if "stepstone" in func.__name__:
                            return jsonify({
                                "jobs": [
                                    {
                                        "title": "Schnelle Beispiel-Anzeige (Timeout)",
                                        "company": "API Timeout GmbH",
                                        "location": request.args.get('city', 'Irgendwo'),
                                        "url": "https://www.stepstone.de/",
                                        "source": "stepstone (timeout)"
                                    }
                                ],
                                "timeoutOccurred": True,
                                "databaseAvailable": verify_database_connection(),
                                "executionTime": elapsed_time
                            })
                        elif "monster" in func.__name__:
                            return jsonify({
                                "jobs": [
                                    {
                                        "title": "Schnelle Beispiel-Anzeige (Timeout)",
                                        "company": "API Timeout GmbH",
                                        "location": request.args.get('city', 'Irgendwo'),
                                        "url": "https://www.monster.de/",
                                        "source": "monster (timeout)"
                                    }
                                ],
                                "timeoutOccurred": True,
                                "databaseAvailable": verify_database_connection(),
                                "executionTime": elapsed_time
                            })
                    
                    return result
                except Exception as e:
                    logger.error(f"Fehler in {func.__name__}: {e}")
                    # Fallback bei Fehlern
                    return jsonify({
                        "jobs": [],
                        "error": str(e),
                        "timeoutOccurred": False,
                        "databaseAvailable": verify_database_connection(),
                        "executionTime": time.time() - start_time
                    })
            
            return wrapper
        return decorator
    
    @app.route("/api/status")
    def api_status():
        """API Status Check - kann länger dauern, da hier die Datenbankverbindung geprüft wird"""
        start_time = time.time()
        
        db_status = False
        db_schema_ok = False
        connection_error = None
        
        # Versuche Datenbankverbindung zu überprüfen
        try:
            db_status = verify_database_connection()
            logger.info(f"Datenbank-Status: {'verbunden' if db_status else 'nicht verbunden'}")
            
            # Versuche Tabellen zu erstellen, falls nötig und DB verfügbar ist
            if db_status and db_imports_successful:
                db_schema_ok = create_tables_if_not_exist()
                if db_schema_ok:
                    logger.info("Datenbank-Schema erfolgreich überprüft/erstellt")
                else:
                    logger.warning("Datenbank-Schema konnte nicht erstellt werden")
        except Exception as e:
            logger.error(f"Fehler bei der Datenbankstatusüberprüfung: {type(e).__name__}: {e}")
            connection_error = f"{type(e).__name__}: {str(e)}"
        
        # Railway- und Datenbankumgebungsvariablen prüfen
        railway_vars = {k: "vorhanden" for k in os.environ if k.startswith("RAILWAY_")}
        db_vars = {
            "DATABASE_URL": "vorhanden" if os.environ.get("DATABASE_URL") else "nicht gesetzt",
            "DATABASE_PUBLIC_URL": "vorhanden" if os.environ.get("DATABASE_PUBLIC_URL") else "nicht gesetzt",
            "POSTGRES_URL": "vorhanden" if os.environ.get("POSTGRES_URL") else "nicht gesetzt"
        }
        
        # Ermittle die Ausführungszeit
        execution_time = time.time() - start_time
        
        return jsonify({
            "status": "online",
            "database": {
                "status": "connected" if db_status else "disconnected",
                "schema": "ok" if db_schema_ok else "not_available",
                "imports": "available" if db_imports_successful else "unavailable",
                "error": connection_error
            },
            "environment": {
                "railway": railway_vars,
                "database": db_vars,
                "host": socket.gethostname(),
                "python": sys.version
            },
            "version": "1.0.0",
            "uptime_seconds": int(time.time() - process_start_time),
            "response_time_seconds": round(execution_time, 3),
            "timestamp": datetime.now().isoformat()
        })
    
    @app.route("/api/stepstone", methods=["GET"])
    @timeout_handler(timeout_seconds=15)  # Timeout erhöht
    def get_stepstone():
        start_time = time.time()
        logger.info("Stepstone API-Anfrage empfangen")
        
        title = request.args.get('title', '')
        city = request.args.get('city', '')
        
        # Protokolliere die Anfrageparameter
        logger.info(f"Stepstone-Suche: Titel={title}, Stadt={city}")
        
        # Starten des Scraping-Prozesses
        scrape_start = time.time()
        jobs = find_stepstone_jobs(title, city)
        scrape_duration = time.time() - scrape_start
        logger.info(f"Stepstone-Scraping abgeschlossen in {scrape_duration:.2f}s, {len(jobs)} Jobs gefunden")
        
        # Versuche, die Jobs in der Datenbank zu speichern
        db_available = verify_database_connection()
        if db_available:
            try:
                save_new_jobs(jobs)
                logger.info(f"Jobs in Datenbank gespeichert")
            except Exception as e:
                logger.error(f"Fehler beim Speichern in Datenbank: {e}")
        
        execution_time = time.time() - start_time
        response = {
            "jobs": jobs,
            "databaseAvailable": db_available,
            "timeoutOccurred": False,  # Wird durch den Decorator überschrieben, wenn nötig
            "executionTime": execution_time,
            "scrapingTime": scrape_duration
        }
        
        logger.info(f"Stepstone-Route abgeschlossen in {execution_time:.2f}s")
        return jsonify(response)
    
    @app.route("/api/monster", methods=["GET"])
    @timeout_handler(timeout_seconds=15)  # Timeout erhöht
    def get_monster():
        start_time = time.time()
        logger.info("Monster API-Anfrage empfangen")
        
        title = request.args.get('title', '')
        city = request.args.get('city', '')
        
        # Protokolliere die Anfrageparameter
        logger.info(f"Monster-Suche: Titel={title}, Stadt={city}")
        
        # Starten des Scraping-Prozesses
        scrape_start = time.time()
        jobs = find_monster_jobs(title, city)
        scrape_duration = time.time() - scrape_start
        logger.info(f"Monster-Scraping abgeschlossen in {scrape_duration:.2f}s, {len(jobs)} Jobs gefunden")
        
        # Versuche, die Jobs in der Datenbank zu speichern
        db_available = verify_database_connection()
        if db_available:
            try:
                save_new_jobs(jobs)
                logger.info(f"Jobs in Datenbank gespeichert")
            except Exception as e:
                logger.error(f"Fehler beim Speichern in Datenbank: {e}")
        
        execution_time = time.time() - start_time
        response = {
            "jobs": jobs,
            "databaseAvailable": db_available,
            "timeoutOccurred": False,  # Wird durch den Decorator überschrieben, wenn nötig
            "executionTime": execution_time,
            "scrapingTime": scrape_duration
        }
        
        logger.info(f"Monster-Route abgeschlossen in {execution_time:.2f}s")
        return jsonify(response)
    
    @app.route('/api/db', methods=['GET'])
    def get_db_jobs():
        """Endpoint zum Abrufen von Jobs aus der Datenbank"""
        start_time = time.time()
        
        title = request.args.get('title', '')
        city = request.args.get('city', '')
        source = request.args.get('source', '')
        
        logger.info(f"Datenbank-Abfrage: Titel={title}, Stadt={city}, Quelle={source}")
        
        # Versuche, die Jobs aus der Datenbank zu laden
        db_available = verify_database_connection()
        if not db_available:
            return jsonify({
                "jobs": [],
                "databaseAvailable": False,
                "error": "Datenbank nicht verfügbar",
                "executionTime": time.time() - start_time
            })
        
        try:
            jobs = get_jobs_by_criteria(title, city, source)
            execution_time = time.time() - start_time
            logger.info(f"{len(jobs)} Jobs aus Datenbank abgerufen in {execution_time:.2f}s")
            
            return jsonify({
                "jobs": jobs,
                "databaseAvailable": True,
                "executionTime": execution_time
            })
        except Exception as e:
            logger.error(f"Fehler beim Abrufen aus Datenbank: {e}")
            return jsonify({
                "jobs": [],
                "databaseAvailable": True,
                "error": str(e),
                "executionTime": time.time() - start_time
            })
            
    return app

def create_fallback_index(app):
    """Erstellt eine Fallback-Startseite, wenn keine im Static-Ordner gefunden wird"""
    try:
        os.makedirs(app.static_folder, exist_ok=True)
        with open(os.path.join(app.static_folder, 'index.html'), 'w') as f:
            f.write("<html><body><h1>Jobbig Job Crawler</h1><p>The API is available at /api/</p><p>Info: Fallback-Index (static files not found)</p></body></html>")
        logger.info("Created fallback index.html")
    except Exception as e:
        logger.error(f"Error creating fallback index: {e}")

# Erstelle die App bei Import
app = create_app()

# Versuche Tabellen zu erstellen, falls DB verfügbar ist
if db_imports_successful:
    try:
        logger.info("Prüfe Datenbankverbindung und Schema beim Start")
        db_ok = verify_database_connection()
        if db_ok:
            schema_ok = create_tables_if_not_exist()
            logger.info(f"Datenbank-Schema-Status: {'OK' if schema_ok else 'Fehler'}")
        else:
            logger.warning("Keine Datenbankverbindung beim Start")
    except Exception as e:
        logger.error(f"Fehler bei der Datenbankinitialisierung: {e}")
        logger.warning("Anwendung läuft im eingeschränkten Modus ohne Datenbankfunktionalität")

# Wenn diese Datei direkt ausgeführt wird
if __name__ == "__main__":
    # Starte den Server im Debug-Modus
    logger.info("Server wird im Debug-Modus gestartet auf 0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, debug=True)