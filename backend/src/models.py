"""SQLAlchemy models for Jobbig."""

import logging
import os

# Logging konfigurieren
logger = logging.getLogger(__name__)

# Versuchen, zusätzliche Module zu installieren, falls sie fehlen
try:
    import subprocess
    logger.info("Versuche, fehlende Datenbankmodule zu installieren...")
    
    # Liste der zu installierenden Module
    db_modules = ["Flask-SQLAlchemy==3.0.5", "SQLAlchemy==1.4.41", "psycopg2-binary", "psycopg", "psycopg2"]
    for module in db_modules:
        try:
            subprocess.check_call(["pip", "install", module, "--no-cache-dir"])
            logger.info(f"Modul {module} erfolgreich installiert")
        except Exception as e:
            logger.warning(f"Konnte Modul {module} nicht installieren: {e}")
except Exception as e:
    logger.warning(f"Konnte zusätzliche Module nicht installieren: {e}")

# Bedingte Importe für SQLAlchemy - darf nicht fehlschlagen für Healthcheck
try:
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy()
    sqlalchemy_available = True
    logger.info("SQLAlchemy erfolgreich importiert")
except ImportError as e:
    sqlalchemy_available = False
    db = None  # Dummy-Variable
    logger.warning(f"SQLAlchemy konnte nicht importiert werden: {e}")

# Definition nur wenn SQLAlchemy verfügbar ist
if sqlalchemy_available:
    class Job(db.Model):
        """ Jobs are jobs """

        __tablename__ = "jobs"

        id = db.Column(
            db.Integer,
            primary_key=True,
        )

        title = db.Column(db.String(200), nullable=False)

        company = db.Column(db.String(200), nullable=False)

        location = db.Column(db.String(200), nullable=False)

        url = db.Column(db.String(200), nullable=False)

        source = db.Column(db.String(200), nullable=False)

else:
    # Dummy-Klasse für den Fall, dass SQLAlchemy nicht verfügbar ist
    class Job:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


def refresh_db():
    """ Delete all job entries and restart the counting """
    if not sqlalchemy_available:
        logger.warning("SQLAlchemy nicht verfügbar, Datenbank kann nicht zurückgesetzt werden")
        return

    try:
        db.session.query(Job).delete()
        db.session.execute("ALTER SEQUENCE jobs_id_seq RESTART WITH 1")
        db.session.commit()
        logger.info("Datenbank erfolgreich zurückgesetzt")
    except Exception as e:
        logger.error(f"Fehler beim Zurücksetzen der Datenbank: {e}")
        # Bei einem Fehler versuchen wir einen Rollback
        try:
            db.session.rollback()
            logger.info("Datenbank-Rollback erfolgreich")
        except Exception as rollback_error:
            logger.error(f"Fehler beim Rollback: {rollback_error}")


def connect_db(app):
    """Connect this database to provided Flask app."""
    if not sqlalchemy_available:
        logger.warning("SQLAlchemy nicht verfügbar, Datenbank kann nicht verbunden werden")
        return False
    
    # Prüfe, ob DATABASE_URL gesetzt ist
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        database_url = os.environ.get("DATABASE_PUBLIC_URL")
    
    if not database_url:
        logger.warning("Keine Datenbank-URL gefunden, Datenbank kann nicht verbunden werden")
        return False
        
    # Railway verwendet 'postgres://' anstatt 'postgresql://'
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        logger.info("Datenbankstring von postgres:// auf postgresql:// korrigiert")
        
    try:
        db.app = app
        db.init_app(app)
        logger.info("Datenbank erfolgreich verbunden")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Verbinden der Datenbank: {type(e).__name__}: {e}")
        return False


def serialize_job(job):
    """Serialize a job SQLAlchemy obj to dictionary."""
    try:
        if job is None:
            return {}
            
        # Wenn es ein Wörterbuch ist, geben wir es direkt zurück
        if isinstance(job, dict):
            return job
            
        return {
            "id": getattr(job, 'id', 0),
            "title": getattr(job, 'title', ''),
            "company": getattr(job, 'company', ''),
            "location": getattr(job, 'location', ''),
            "url": getattr(job, 'url', ''),
            "source": getattr(job, 'source', ''),
        }
    except Exception as e:
        logger.error(f"Fehler beim Serialisieren eines Jobs: {e}")
        # Fallback für den Fall, dass es ein einfaches Dictionary ist
        if isinstance(job, dict):
            return job
        # Andernfalls ein leeres Dictionary zurückgeben
        return {}