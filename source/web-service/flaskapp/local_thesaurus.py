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
    r_label = csv_line[0]
    r_id = csv_line[1]
    r_sn = csv_line[2]
    r_exact_match = csv_line[3].split(", ")

    r["@context"] = "https://linked.art/ns/v1/linked-art.json"
    r["id"] = r_id
    r["type"] = "Type"
    r["_label"] = r_label

    # identified_by
    ident_by_list = []
    ident_by = {}
    ident_by["type"] = "Name"
    class_as_list = []
    class_as = {}
    class_as["id"] = "http://vocab.getty.edu/aat/300404670"
    class_as["type"] = "Type"
    class_as["_label"] = "Primary Name"
    class_as_list.append(class_as)
    ident_by["classified_as"] = class_as
    ident_by["content"] = r_label
    lang_list = []
    lang = {}
    lang["id"] = "http://vocab.getty.edu/aat/300388277"
    lang["type"] = "Language"
    lang["_label"] = "English"
    lang_list.append(lang)
    ident_by["language"] = lang_list
    ident_by_list.append(ident_by)
    r["identified_by"] = ident_by_list

    # referred_to_by
    ref_to_by_list = []
    ref_to_by = {}
    ref_to_by["type"] = "LinguisticObject"
    class_as_list = []
    class_as = {}
    class_as["id"] = "http://vocab.getty.edu/aat/300435416"
    class_as["type"] = "Type"
    class_as["_label"] = "Description"
    class_as_int_list = []
    class_as_int = {}
    class_as_int["id"] = "http://vocab.getty.edu/aat/300418049"
    class_as_int["type"] = "Type"
    class_as_int["_label"] = "Brief Text"
    class_as_int_list.append(class_as_int)
    class_as["classified_as"] = class_as_int_list
    class_as_list.append(class_as)
    ref_to_by["classified_as"] = class_as_list
    ref_to_by["content"] = r_sn
    ref_to_by_list.append(ref_to_by)
    r["referred_to_by"] = ref_to_by_list

    # exact_match
    r["exact_match"] = r_exact_match

    return json.dumps(r)


def read_csv_file():
    download = requests.get(current_app.config["LOCAL_THESAURUS_URL"])
    decoded = download.content.decode("utf-8")
    cr = csv.reader(decoded.splitlines(), delimiter=",")
    return list(cr)
