from flaskapp.models import db
from sqlalchemy import ForeignKey, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import deferred

# Keeping the old columns to allow for migration
class Record(db.Model):
    __tablename__ = "records"
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.String, nullable=False, index=True, unique=True)
    entity_type = db.Column(db.String, index=True)
    datetime_created = db.Column(db.TIMESTAMP, nullable=False, index=True)
    datetime_updated = db.Column(
        DateTime(),
        onupdate=func.now(),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    datetime_deleted = db.Column(db.TIMESTAMP)
    data = deferred(db.Column(db.JSON))
    previous_version = db.Column(db.String, nullable=True)
    is_old_version = db.Column(db.Boolean, nullable=True, default=False)
    checksum = db.Column(db.String, nullable=True)


Index("ix_records_record_id_and_type", Record.entity_id, Record.entity_type)


class Version(db.Model):
    __tablename__ = "versions"
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.String, nullable=False, index=True, unique=True)
    entity_type = db.Column(db.String, index=True)
    datetime_created = deferred(db.Column(db.TIMESTAMP, nullable=False))
    datetime_updated = db.Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        server_default=func.now(),
        index=True,
    )
    datetime_deleted = db.Column(db.TIMESTAMP)
    data = deferred(db.Column(db.JSON))
    checksum = deferred(db.Column(db.String, nullable=True))
    record_id = db.Column(db.Integer, ForeignKey("records.id"))
    record = db.relationship(
        "Record",
        backref=db.backref(
            "versions", lazy="select", order_by="Version.datetime_updated.desc()"
        ),
    )


Index(
    "ix_versions_chronological_lookup",
    Version.record_id,
    Version.datetime_updated,
    Version.entity_id,
    postgresql_using="btree",
    postgresql_ops={"datetime_updated": "DESC"},
)
