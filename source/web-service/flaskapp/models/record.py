from flaskapp.models import db


class Record(db.Model):
    __tablename__ = "records"
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String, nullable=False)
    datetime_created = db.Column(db.TIMESTAMP(timezone=True))
    datetime_updated = db.Column(db.TIMESTAMP(timezone=True))
    datetime_published = db.Column(db.TIMESTAMP(timezone=True))
    namespace = db.Column(db.String, nullable=False)
    entity = db.Column(db.String, nullable=False)
    data = db.Column(db.JSON)
    counter = db.Column(db.Integer, default=0, nullable=False)
