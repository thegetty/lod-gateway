from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models so SQLAlchemy knows about them for create_all()
from flaskapp.models.activity import Activity
from flaskapp.models.record import Record, Version
from flaskapp.models.container import LDPContainer, LDPContainerContents
