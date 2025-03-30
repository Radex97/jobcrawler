"""SQLAlchemy models for Jobbig."""

from flask_sqlalchemy import SQLAlchemy

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
    db.session.query(Job).delete()
    db.session.execute("ALTER SEQUENCE jobs_id_seq RESTART WITH 1")
    db.session.commit()


def connect_db(app):
    """Connect this database to provided Flask app."""

    db.app = app
    db.init_app(app)


def serialize_job(job):
    """Serialize a job SQLAlchemy obj to dictionary."""

    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "source": job.source,
    }