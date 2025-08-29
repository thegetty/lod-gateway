import json
import uuid

from flask import current_app

from flaskapp.models import db
from flaskapp.models.record import Record, Version
from flaskapp.models.activity import Activity
from flaskapp.models.container import LDPContainer, NoLDPContainerFoundError

from .container import handle_container_requirements

from datetime import datetime, timezone

from flaskapp.errors import (
    status_nt,
    status_id_missing,
    status_ok,
)
from flaskapp.utilities import checksum_json, Event


def get_record(rec_id, also_containers=True):
    if (
        result := db.session.query(Record)
        .filter(Record.entity_id == rec_id)
        .one_or_none()
    ):
        return {"record": result}
    elif current_app.config["LDP_BACKEND"] and also_containers:
        if (
            result := db.session.query(LDPContainer)
            .filter(LDPContainer.container_identifier == rec_id)
            .one_or_none()
        ):
            return {"container": result}
    return None


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
def record_create(input_rec, commit=False, process_activity=False):
    r = Record()
    id_attr = "@id" if "@id" in input_rec else "id"
    entity_id = input_rec[id_attr]
    entity_type = None
    # 'entity_type' is not required, so check if exists
    if "type" in input_rec.keys():
        entity_type = input_rec["type"]
    elif "@type" in input_rec.keys():
        entity_type = input_rec["@type"]

    parent_container = None
    # If LDP backend is enabled, ensure there is a container to add this to:
    if current_app.config["LDP_BACKEND"]:
        # This either checks to see that the necessary parent container exists and returns it
        # or, if LDP_AUTOCREATE_CONTAINERS flag is true, this will optimistically create the
        # necessary container 'chain' as part of this transaction, with the connections as needed
        # and return the final container object
        try:
            parent_container = handle_container_requirements(entity_id, entity_type)
        except NoLDPContainerFoundError as e:
            current_app.logger.error(f"Required LDP Container not found: {str(e)}")
            raise

    r = Record(entity_id=entity_id, entity_type=entity_type)
    r.datetime_created = datetime.now(timezone.utc)
    r.datetime_updated = r.datetime_created
    r.datetime_deleted = None
    r.data = input_rec
    r.checksum = checksum_json(input_rec)

    db.session.add(r)
    db.session.flush()

    if parent_container is not None:
        parent_container.add_to_container(
            r, db_dialect=current_app.config["DB_DIALECT"]
        )
        current_app.logger.debug(
            f"Created {r.entity_id} and added to {parent_container.container_identifier}"
        )

    if process_activity is True:
        process_activity(entity_id, Event.Create)

    if commit is True:
        db.session.commit()

    # primary key of the newly created record
    return r.id


# Do not return anything. Calling function has all the info
def record_update(db_rec, input_rec, commit=False, process_activity=False):
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

    # Will ONLY try to assert the container structure if the autocreate setting is on.
    if (
        current_app.config["LDP_BACKEND"]
        and current_app.config["LDP_AUTOCREATE_CONTAINERS"] is True
    ):
        # This will assert or reassert the containers required for this item on update:
        try:
            parent_container = handle_container_requirements(
                db_rec.entity_id, db_rec.entity_type
            )
            parent_container.add_to_container(
                db_rec, db_dialect=current_app.config["DB_DIALECT"]
            )
            current_app.logger.debug(
                f"Asserted {db_rec.entity_id} as part of {parent_container.container_identifier}"
            )
        except NoLDPContainerFoundError as e:
            current_app.logger.error(
                f"Required LDP Container could not be created?: {str(e)}"
            )
            raise

    if process_activity is True:
        process_activity(db_rec.entity_id, Event.Update)

    if commit is True:
        db.session.commit()


# Delete record by leaving a stub record (no .data, w/ a datatime_deleted.)
def record_delete(db_rec, input_rec, commit=False, process_activity=False):
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

    parent_container = None
    # If LDP backend is enabled, ensure there is a container to add this to:
    if current_app.config["LDP_BACKEND"]:
        # This either checks to see that the necessary parent container exists and returns it
        # or, if LDP_AUTOCREATE_CONTAINERS flag is true, this will optimistically create the
        # necessary container 'chain' as part of this transaction, with the connections as needed
        # and return the final container object
        try:
            parent_container = handle_container_requirements(
                db_rec.entity_id, db_rec.entity_type
            )
        except NoLDPContainerFoundError as e:
            current_app.logger.error(f"Required LDP Container not found: {str(e)}")
            raise

    current_app.logger.debug(f"Deleting {db_rec.entity_id}")
    db_rec.data = None
    db_rec.checksum = None
    db_rec.datetime_deleted = datetime.now(timezone.utc)

    if parent_container is not None:
        removed_from_container = parent_container.remove_from_container(
            db_rec, db_dialect=current_app.config["DB_DIALECT"]
        )
        current_app.logger.debug(
            f"Removed {db_rec.entity_id} from {parent_container.container_identifier}? {removed_from_container}"
        )

    if process_activity is True:
        process_activity(db_rec.entity_id, Event.Delete)

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
