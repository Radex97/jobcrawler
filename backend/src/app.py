from .models import Job, db, connect_db, refresh_db, serialize_job
from flask import Flask, cli, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import logging
from .scraping import find_monster_jobs, find_stepstone_jobs

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# creating the Flask application
app = Flask(__name__, static_folder='static', static_url_path='')

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
    static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    logger.info(f"Static folder path: {static_path}")
    
    # Prüfen, ob der statische Ordner existiert
    if os.path.exists(static_path):
        logger.info(f"Static folder exists: {os.listdir(static_path)}")
    else:
        logger.warning(f"Static folder does not exist: {static_path}")
        try:
            os.makedirs(static_path, exist_ok=True)
            with open(os.path.join(static_path, 'index.html'), 'w') as f:
                f.write("<html><body><h1>Jobbig Job Crawler</h1><p>The API is available at /api/</p></body></html>")
            logger.info("Created fallback index.html")
        except Exception as e:
            logger.error(f"Error creating static folder: {e}")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files or the SPA"""
    logger.info(f"Request for path: {path}")
    
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        try:
            logger.info(f"Serving index.html for path: {path}")
            return send_from_directory(app.static_folder, 'index.html')
        except Exception as e:
            logger.error(f"Error serving index.html: {e}")
            return "Jobbig API is running", 200

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