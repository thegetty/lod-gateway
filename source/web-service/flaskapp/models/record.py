from flaskapp.models import db


class Record(db.Model):
    __tablename__ = "records"
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.String, nullable=False, index=True, unique=True)
    entity_type = db.Column(db.String, index=True)
    datetime_created = db.Column(db.TIMESTAMP, nullable=False)
    datetime_updated = db.Column(db.TIMESTAMP, nullable=False)
    datetime_deleted = db.Column(db.TIMESTAMP)
    data = db.Column(db.JSON)
    previous_version = db.Column(db.String, nullable=True, index=True)
    is_old_version = db.Column(db.Boolean, nullable=True, default=False)
    checksum = db.Column(db.String, nullable=True)
