"""SQLAlchemy models for Jobbig."""

import logging

# Logging konfigurieren
logger = logging.getLogger(__name__)

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
        
    try:
        db.app = app
        db.init_app(app)
        logger.info("Datenbank erfolgreich verbunden")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Verbinden der Datenbank: {e}")
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
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "source": job.source,
        }
    except Exception as e:
        logger.error(f"Fehler beim Serialisieren eines Jobs: {e}")
        # Fallback für den Fall, dass es ein einfaches Dictionary ist
        if isinstance(job, dict):
            return job
        # Andernfalls ein leeres Dictionary zurückgeben
        return {}