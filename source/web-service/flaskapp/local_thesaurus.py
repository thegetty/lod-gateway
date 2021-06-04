from uuid import uuid4
from datetime import datetime
from flaskapp.models import db
from flaskapp.models.record import Record


def populate_db(context):
    with context:
        db.create_all()
        insert_fake_record_set()
        

def insert_fake_record_set():
    rec_set = create_fake_record_set()   
    for r in rec_set:
        db.session.add(r)
    db.session.commit()


def create_fake_record():
    return Record(
        entity_id=str(uuid4()),
        entity_type="Object",
        datetime_created=datetime.utcnow(),
        datetime_updated=datetime.utcnow(),
        data={"example": "data"},
    )


def create_fake_record_set():
    result = []
    for n in range(100):
        result.append(create_fake_record())
    return result
