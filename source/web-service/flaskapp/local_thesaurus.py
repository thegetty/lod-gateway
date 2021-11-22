from datetime import datetime
from flask import current_app
from flaskapp.models import db
from flaskapp.routes import ingest
from flaskapp.models.record import Record
import requests
import csv
import json


def populate_db(context):
    with context:
        db.create_all()
        csv_line_list = read_csv_file()
        insert_record_set(csv_line_list)


def insert_record_set(csv_line_list):
    rec_set = []
    for csv_line in csv_line_list:
        # this is our key - must be unique
        if csv_line[1] == "":
            continue
        r = create_record(csv_line)
        rec_set.append(r)
    ingest.process_record_set(rec_set)


def create_record(csv_line):
    r = {}
    r["@context"] = "https://static.getty.edu/contexts/skos/skos-lite.json"
    r["id"] = csv_line[1]
    r["type"] = "Concept"
    if len(csv_line[0]) == 0:
        r["pref_label"] = None
    else:
        r["pref_label"] = csv_line[0]
    if len(csv_line[2]) == 0:
        r["scope_note"] = None
    else:
        r["scope_note"] = csv_line[2]
    if len(csv_line[3]) == 0:
        r["exact_match"] = None
    else:
        r["exact_match"] = csv_line[3].split(", ")
    return json.dumps(r)


def read_csv_file():
    download = requests.get(current_app.config["LOCAL_THESAURUS_URL"])
    decoded = download.content.decode("utf-8")
    cr = csv.reader(decoded.splitlines(), delimiter=",")
    return list(cr)
