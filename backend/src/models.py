"""SQLAlchemy models for Jobbig."""

from flask_sqlalchemy import SQLAlchemy
import logging

# Logging konfigurieren
logger = logging.getLogger(__name__)

db = SQLAlchemy()


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
    try:
        db.app = app
        db.init_app(app)
        logger.info("Datenbank erfolgreich verbunden")
    except Exception as e:
        logger.error(f"Fehler beim Verbinden der Datenbank: {e}")
        raise  # Den Fehler weitergeben, damit die aufrufende Funktion weiß, dass es ein Problem gab


def serialize_job(job):
    """Serialize a job SQLAlchemy obj to dictionary."""
    try:
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