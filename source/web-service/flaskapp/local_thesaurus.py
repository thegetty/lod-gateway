from uuid import uuid4
from datetime import datetime
from flaskapp.models import db
from flaskapp.models.record import Record
import requests
import csv


def populate_db(context):
    with context:
        db.create_all()
        csv_line_list = read_csv_file()
        insert_record_set(csv_line_list)


def insert_record_set(csv_line_list):
    for csv_line in csv_line_list:
        r = create_record(csv_line)
        if r == None:
            continue
        db.session.add(r)
    db.session.commit()


def create_record(csv_line):
    if csv_line[1] == "":
        return None

    return Record(
        entity_id=csv_line[1],
        entity_type="Type",
        datetime_created=datetime.utcnow(),
        datetime_updated=datetime.utcnow(),
        data=create_lt_data(csv_line),
    )


def create_lt_data(csv_line):
    return {
        "context": "https://static.getty.edu/contexts/linked.art/ns/v1.1.0/linked-art.json",
        "skos:prefLabel": csv_line[0],
        "skos:scopeNote": csv_line[2],
    }


def read_csv_file():
    download = requests.get("http://aata2-stage.getty.edu")
    decoded = download.content.decode("utf-8")
    cr = csv.reader(decoded.splitlines(), delimiter=",")
    return list(cr)
