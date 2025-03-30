from .models import Job, db, connect_db, refresh_db, serialize_job
from flask import Flask, cli, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import logging
import glob
from .scraping import find_monster_jobs, find_stepstone_jobs

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# creating the Flask application
app = Flask(__name__, static_folder=static_dir, static_url_path='')

# activate CORS for flask app
CORS(app, resources={r"/*": {"origins": "*"}})

# load .env variables
try:
    cli.load_dotenv(".env")
except:
    logger.info("Keine .env Datei gefunden oder Fehler beim Laden")

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

try:
    connect_db(app)
    db.create_all()
    logger.info("Datenbank erfolgreich verbunden und Tabellen erstellt")
except Exception as e:
    logger.error(f"Fehler bei der Datenbankverbindung: {e}")
    # Nicht abbrechen, damit der Healthcheck trotzdem funktioniert

# Überprüfung des statischen Ordners
@app.before_first_request
def check_static_folder():
    try:
        logger.info(f"Static folder path: {app.static_folder}")
        
        # Prüfen, ob der statische Ordner existiert
        if os.path.exists(app.static_folder):
            files = os.listdir(app.static_folder)
            logger.info(f"Static folder exists with {len(files)} files: {files[:10]}")
            
            # Überprüfen, ob index.html existiert
            if 'index.html' not in files:
                logger.warning("index.html not found in static folder")
                create_fallback_index()
        else:
            logger.warning(f"Static folder does not exist: {app.static_folder}")
            create_fallback_index()
            
        # Suche auch nach anderen möglichen statischen Verzeichnissen
        possible_static_dirs = glob.glob('/app/**/static', recursive=True)
        logger.info(f"Other possible static directories: {possible_static_dirs}")
    except Exception as e:
        logger.error(f"Error checking static folder: {e}")

def create_fallback_index():
    try:
        os.makedirs(app.static_folder, exist_ok=True)
        with open(os.path.join(app.static_folder, 'index.html'), 'w') as f:
            f.write("<html><body><h1>Jobbig Job Crawler</h1><p>The API is available at /api/</p><p>Info: Fallback-Index (static files not found)</p></body></html>")
        logger.info("Created fallback index.html")
    except Exception as e:
        logger.error(f"Error creating fallback index: {e}")

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

@app.route("/health")
def health():
    """Health check endpoint"""
    return "OK", 200

@app.route("/api/stepstone", methods=["GET"])
def get_stepstone():
    """ Get jobs from Stepstone """
    try:
        refresh_db()
        title = request.args.get("title")
        city = request.args.get("city")
        stepstone_jobs = find_stepstone_jobs(title, city)

        for item in stepstone_jobs:
            job = Job(
                title=item["title"],
                company=item["company"],
                location=item["location"],
                url=item["url"],
                source="stepstone",
            )
            db.session.add(job)

        db.session.commit()
        jobs = Job.query.filter_by(source="stepstone").all()
        serialized = [serialize_job(j) for j in jobs]
        return jsonify(serialized)
    except Exception as e:
        logger.error(f"Fehler in Stepstone-Route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/monster", methods=["GET"])
def get_monster():
    """ Get jobs from Monster """
    try:
        refresh_db()
        title = request.args.get("title")
        city = request.args.get("city")
        monster_jobs = find_monster_jobs(title, city)

        for item in monster_jobs:
            job = Job(
                title=item["title"],
                company=item["company"],
                location=item["location"],
                url=item["url"],
                source="monster",
            )
            db.session.add(job)

        db.session.commit()
        jobs = Job.query.filter_by(source="monster").all()
        serialized = [serialize_job(j) for j in jobs]
        return jsonify(serialized)
    except Exception as e:
        logger.error(f"Fehler in Monster-Route: {e}")
        return jsonify({"error": str(e)}), 500