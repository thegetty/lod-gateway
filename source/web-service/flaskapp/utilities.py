from datetime import datetime
from enum import Enum


# Enum with possible database events
# Used in 'ingest' and tests
class Event(Enum):
    Create = 1
    Update = 2
    Delete = 3
    Move = 4


# Format datetime in form 'yyyy-mm-dd hh:mm:ss'
# Used across the app
def format_datetime(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")
