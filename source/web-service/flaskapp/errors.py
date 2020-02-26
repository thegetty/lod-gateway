import json
from collections import namedtuple

from flask import current_app


# Set of all possible errors statuses encapsulated in named tuple structure.
status_nt = namedtuple("name", "code title detail")

status_ok = status_nt(200, "OK", "OK")
status_wrong_syntax = status_nt(422, "Invalid JSON", "Could not parse JSON record")
status_id_missing = status_nt(422, "ID Missing", "ID for the JSON record not found")
status_data_missing = status_nt(422, "Data Missing", "No input data found")
status_wrong_auth_token = status_nt(
    401, "Wrong Authorization Token", "Authorization token is wrong or missing"
)
status_record_not_found = status_nt(
    404, "Record Not Found", "Unable to obtain matching record from database"
)
status_page_not_found = status_nt(404, "Page Not Found", "Page number out of bounds")
status_GET_not_allowed = status_nt(
    405, "Forbidden Method", "For the requested URL only 'POST' method is allowed"
)
status_db_error = status_nt(
    500, "Data Base Error", "DB connection cannot be established"
)
status_db_save_error = status_nt(
    503, "Service Unavalable", "Cannot perform database operation"
)


# Construct 'error response' object
def construct_error_response(status, source=None):

    err = {}
    err["status"] = status.code

    # include 'line_number' only when needed
    if source:
        err["source"] = {"line number": source}

    err["title"] = status.title
    err["detail"] = status.detail
    err = [err]
    result = {"errors": err}

    response = current_app.response_class(
        response=json.dumps(result), mimetype="application/json", status=status.code,
    )

    return response
