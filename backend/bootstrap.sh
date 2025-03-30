#!/bin/bash
export FLASK_APP=./src/app.py
source $(pipenv --venv)/bin/activate
flask run -h 0.0.0.0