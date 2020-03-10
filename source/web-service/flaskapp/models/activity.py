from flaskapp.models import db


class Activity(db.Model):
    __tablename__ = "activities"
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String, nullable=False, index=True, unique=True)
    datetime_created = db.Column(db.TIMESTAMP, nullable=False)
    record_id = db.Column(
        db.Integer, db.ForeignKey("records.id"), index=True, nullable=False
    )
    record = db.relationship("Record", backref=db.backref("activities", lazy=True))
    event = db.Column(db.String, nullable=False)
