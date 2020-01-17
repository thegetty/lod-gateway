from flaskapp.models import db


class Activity(db.Model):
    __tablename__ = "activities"
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String, nullable=False)
    datetime_created = db.Column(db.TIMESTAMP(timezone=True))
    datetime_updated = db.Column(db.TIMESTAMP(timezone=True))
    datetime_published = db.Column(db.TIMESTAMP(timezone=True))
    datetime_started = db.Column(db.TIMESTAMP(timezone=True))
    datetime_ended = db.Column(db.TIMESTAMP(timezone=True))
    namespace = db.Column(db.String, nullable=False)
    entity = db.Column(db.String, nullable=False)
    record_id = db.Column(db.Integer, db.ForeignKey("records.id"), nullable=False)
    record = db.relationship("Record", backref=db.backref("activities", lazy=True))
    event = db.Column(db.String, nullable=False)
