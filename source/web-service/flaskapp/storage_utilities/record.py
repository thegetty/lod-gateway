import json
import uuid

from flask import current_app

from flaskapp.models import db
from flaskapp.models.record import Record, Version
from flaskapp.models.activity import Activity

from datetime import datetime, timezone

from flaskapp.errors import (
    status_nt,
    status_id_missing,
    status_ok,
)
from flaskapp.utilities import (
    checksum_json,
)


def get_record(rec_id):
    result = db.session.query(Record).filter(Record.entity_id == rec_id).one_or_none()
    return result


# ### VALIDATION FUNCTIONS ###
def validate_record_set(record_list):
    """
    Validate a list of json records.
    Break and return status if at least one record is invalid
    Return line number where the error occured
    """
    for index, rec in enumerate(record_list, start=1):
        status = validate_record(rec)
        if status != status_ok:
            return (status, index)

    else:
        return True


# There is no entry with this 'id'. Create a new record
def record_create(input_rec, commit=False):
    r = Record()
    id_attr = "@id" if "@id" in input_rec else "id"
    r.entity_id = input_rec[id_attr]

    # 'entity_type' is not required, so check if exists
    if "type" in input_rec.keys():
        r.entity_type = input_rec["type"]
    elif "@type" in input_rec.keys():
        r.entity_type = input_rec["@type"]

    r.datetime_created = datetime.now(timezone.utc)
    r.datetime_updated = r.datetime_created
    r.datetime_deleted = None
    r.data = input_rec
    r.checksum = checksum_json(input_rec)

    db.session.add(r)
    db.session.flush()
    if commit is True:
        db.session.commit()

    # primary key of the newly created record
    return r.id


# Do not return anything. Calling function has all the info
def record_update(db_rec, input_rec, commit=False):
    if current_app.config["KEEP_LAST_VERSION"] is True:
        # Versioning
        current_app.logger.info(
            f"Versioning enabled: archiving a copy of {db_rec.entity_id} and replacing current with new data."
        )
        prev_id = str(uuid.uuid4())
        prev = Version()
        prev.entity_id = prev_id
        prev.entity_type = db_rec.entity_type
        # Setting the 'created' date to be equal to when the record was last updated.
        prev.datetime_created = db_rec.datetime_updated
        prev.datetime_updated = db_rec.datetime_updated
        prev.datetime_deleted = db_rec.datetime_deleted
        prev.data = db_rec.data
        prev.checksum = db_rec.checksum
        # Link back to old record
        prev.record = db_rec
        prev.record_id = db_rec.id

        db.session.add(prev)

    # With the update to the model, this should be automatic
    # db_rec.datetime_updated = datetime.now(timezone.utc)
    db_rec.data = input_rec
    db_rec.datetime_deleted = None
    db_rec.checksum = checksum_json(input_rec)

    if commit is True:
        db.session.commit()


# Delete record by leaving a stub record (no .data, w/ a datatime_deleted.)
def record_delete(db_rec, input_rec, commit=False):
    # Versioning
    if current_app.config["KEEP_LAST_VERSION"] is True:
        if current_app.config.get("KEEP_VERSIONS_AFTER_DELETION") is True:
            current_app.logger.info(
                f"KEEP_VERSIONS_AFTER_DELETION enabled: archiving a copy of {db_rec.entity_id} and deleting the current data."
            )
            prev_id = str(uuid.uuid4())
            prev = Version()
            prev.entity_id = prev_id
            prev.entity_type = db_rec.entity_type
            # Setting the 'created' date to be equal to when the record was last updated.
            prev.datetime_created = db_rec.datetime_updated
            prev.datetime_updated = db_rec.datetime_updated
            prev.data = db_rec.data
            prev.checksum = db_rec.checksum
            # Link back to old record
            prev.record = db_rec
            prev.record_id = db_rec.id

            db.session.add(prev)
        else:
            # Hard delete?
            # Remove all old versions?
            current_app.logger.info(
                f"KEEP_VERSIONS_AFTER_DELETION not enabled: also removing all versions of {db_rec.entity_id}."
            )

            for version in db_rec.versions:
                db.session.delete(version)

    current_app.logger.debug(f"Deleting {db_rec.entity_id}")
    db_rec.data = None
    db_rec.checksum = None
    db_rec.datetime_deleted = datetime.now(timezone.utc)

    if commit is True:
        db.session.commit()


def process_activity(prim_key, crud_event, commit=False):
    a = Activity()
    a.uuid = str(uuid.uuid4())
    a.datetime_created = datetime.now(timezone.utc)
    a.record_id = prim_key
    a.event = crud_event.name
    db.session.add(a)

    if commit is True:
        db.session.commit()


def validate_record(rec):
    """
    Validate a single json record.
    Check valid json syntax plus some other params
    """
    try:
        # JSON syntax is good, validate other params
        data = json.loads(rec)

        # return 'id_missing' if no 'id' present
        id_attr = "@id" if "@id" in data.keys() else "id"

        if id_attr not in data.keys():
            return status_id_missing

        # check id_attr is not empty
        if not data[id_attr].strip():
            return status_id_missing

        # all validations succeeded, return OK
        return status_ok

    except Exception as e:
        # JSON syntax is not valid
        current_app.logger.error("JSON Record Parse/Validation Error: " + str(e))
        return status_nt(422, "JSON Record Parse/Validation Error", str(e))
