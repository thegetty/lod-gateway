from datetime import datetime
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
    r[
        "@context"
    ] = "https://static.getty.edu/contexts/linked.art/ns/v1.1.0/linked-art.json"
    r["skos:prefLabel"] = csv_line[0]
    r["skos:scopeNote"] = csv_line[2]
    r["id"] = csv_line[1]
    r["type"] = "Type"
    return json.dumps(r)


def read_csv_file():
    download = requests.get("http://aata2-stage.getty.edu")
    decoded = download.content.decode("utf-8")
    cr = csv.reader(decoded.splitlines(), delimiter=",")
    return list(cr)
