from .models import Job, db, connect_db, refresh_db, serialize_job
from flask import Flask, cli, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from .scraping import find_monster_jobs, find_stepstone_jobs

# creating the Flask application
app = Flask(__name__, static_folder='static', static_url_path='')

# activate CORS for flask app
CORS(app, resources={r"/*": {"origins": "*"}})

# load .env variables
cli.load_dotenv(".env")

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

connect_db(app)
db.create_all()

@app.route("/")
def serve():
    """Serve the frontend application"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route("/api/stepstone", methods=["GET"])
def get_stepstone():
    """ Get jobs from Stepstone """
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

@app.route("/api/monster", methods=["GET"])
def get_monster():
    """ Get jobs from Monster """
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