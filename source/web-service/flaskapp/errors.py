import json
import logging
from collections import namedtuple

from flask import current_app

logger = logging.getLogger(__name__)

# Set of all possible errors statuses encapsulated in named tuple structure.
status_nt = namedtuple("name", "code title detail")

status_ok = status_nt(200, "OK", "OK")
status_not_modified = status_nt(
    304, "Not Modified", "No change was made to the resource."
)

status_bad_auth_header = status_nt(
    400, "Bad Authorization Header", "Syntax of Authorization header is invalid"
)

status_wrong_auth_token = status_nt(
    401, "Wrong Authorization Token", "Authorization token is wrong or missing"
)

status_record_not_found = status_nt(
    404, "Record Not Found", "Unable to obtain matching record from database"
)

status_page_not_found = status_nt(404, "Page Not Found", "Page number out of bounds")

status_pagenum_not_integer = status_nt(404, "Page Not Found", "Wrong page number")

status_GET_not_allowed = status_nt(
    405, "Forbidden Method", "For the requested URL only 'POST' method is allowed"
)

status_patch_method_not_allowed = status_nt(
    405, "Method Not allowed", "This is not a valid target for a PATCH method"
)

status_patch_request_unparsable = status_nt(
    400,
    "Bad Request",
    "This is not a valid request for the PATCH method. Requires a JSON body,"
    " with add and/or delete keys, and a format key indicating the correct RDF serialization type",
)

status_wrong_syntax = status_nt(422, "Invalid JSON", "Could not parse JSON record")

status_id_missing = status_nt(422, "ID Missing", "ID for the JSON record not found")

status_data_missing = status_nt(422, "Data Missing", "No input data found")

status_db_error = status_nt(
    500, "Data Base Error", "DB connection cannot be established"
)

status_graphstore_error = status_nt(
    500, "Graph Store Error", "Graph store connection cannot be established"
)

status_db_save_error = status_nt(
    503, "Service Unavailable", "Cannot perform database operation"
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

    logger.error(err)

    response = current_app.response_class(
        response=json.dumps(result), mimetype="application/json", status=status.code
    )

    if status.code == 503:
        response.headers["Retry-After"] = "30"

    return response
