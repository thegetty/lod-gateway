from flaskapp.models import db
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.sql import func

# Keeping the old columns to allow for migration
class Record(db.Model):
    __tablename__ = "records"
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.String, nullable=False, index=True, unique=True)
    entity_type = db.Column(db.String, index=True)
    datetime_created = db.Column(db.TIMESTAMP, nullable=False, index=True)
    datetime_updated = db.Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        server_default=func.now(),
        index=True,
    )
    datetime_deleted = db.Column(db.TIMESTAMP)
    data = db.Column(db.JSON)
    previous_version = db.Column(db.String, nullable=True, index=True)
    is_old_version = db.Column(db.Boolean, nullable=True, default=False)
    checksum = db.Column(db.String, nullable=True)


class Version(db.Model):
    __tablename__ = "versions"
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.String, nullable=False, index=True, unique=True)
    entity_type = db.Column(db.String, index=True)
    datetime_created = db.Column(db.TIMESTAMP, nullable=False, index=True)
    datetime_updated = db.Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        server_default=func.now(),
        index=True,
    )
    datetime_deleted = db.Column(db.TIMESTAMP)
    data = db.Column(db.JSON)
    checksum = db.Column(db.String, nullable=True)
    record_id = db.Column(db.Integer, ForeignKey("records.id"))
    record = db.relationship(
        "Record",
        backref=db.backref(
            "versions", lazy=True, order_by="Version.datetime_updated.desc()"
        ),
    )
