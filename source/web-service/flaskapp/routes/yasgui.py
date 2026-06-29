from flask_openapi3 import APIBlueprint
from flask import current_app, abort, request
from flaskapp.errors import status_nt, construct_error_response, status_ok
from flaskapp.openapi import sparql_tag
from flaskapp.openapi_models import _strip_openapi_kwargs
from flaskapp.utilities import authenticate_bearer

# Create a new "yasgui" route blueprint
yasgui = APIBlueprint("yasgui", __name__)
_strip_openapi_kwargs(yasgui)


# ### ROUTES ###
@yasgui.get(
    "/sparql-ui",
    tags=[sparql_tag],
    summary="SPARQL UI page",
    responses={
        200: {"description": "HTML page"},
        501: {"description": "RDF not enabled"},
    },
)
def get_yasgui():
    if current_app.config["PROCESS_RDF"] is not True:
        response = construct_error_response(
            status_nt(
                501,
                "Not Implemented",
                "Application is not enabled for SPARQL operations",
            )
        )
        return abort(response)

    endpoint = (
        current_app.config["BASE_URL"]
        + "/"
        + current_app.config["NAMESPACE"]
        + "/sparql"
    )

    if current_app.config["SPARQL_QUERY_AUTHENTICATION"] is True:
        # SPARQL endpoint requires authentication
        status = authenticate_bearer(request, current_app)
        if status != status_ok:
            response = construct_error_response(status)
            return abort(response)

        auth_header = request.headers.get("Authorization")

        # pass on the actual token from "Bearer <token>"
        token = ""
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # /sparql queries requires token:
        yasgui_page = create_yasgui_html(endpoint, token=token)
        return yasgui_page
    else:
        # No authentication required.
        yasgui_page = create_yasgui_html(endpoint)
        return yasgui_page


def create_yasgui_html(endpoint, token=None):
    head = (
        "<head>"
        "<link href='https://unpkg.com/@triply/yasgui/build/yasgui.min.css' rel='stylesheet' type='text/css' />"
        "<script src='https://unpkg.com/@triply/yasgui/build/yasgui.min.js'></script>"
        "</head>"
    )

    if token is not None:
        body = (
            "<body>"
            "<div id='yasgui'></div>"
            "<script>"
            f"const serverToken = '{token}';"
            "const yasgui = new Yasgui(document.getElementById('yasgui'), {"
            "  requestConfig: {"
            f"   endpoint: '{endpoint}',"
            "    bearerAuth: {"
            f"     token: '{token}'"
            "    }"
            "  },"
            "  copyEndpointOnNewTab: false"
            "});"
            "</script>"
            "<style> .yasgui .autocompleteWrapper { visibility: hidden } .yasr .tableControls .tableFilter { margin-right: 10px; height: auto !important; } </style>"
            "</body>"
        )
    else:
        body = (
            "<body>"
            "<div id='yasgui'></div>"
            "<script>"
            "const yasgui = new Yasgui(document.getElementById('yasgui'), "
            "{requestConfig: { endpoint: "
            f"'{endpoint}'"
            "}, copyEndpointOnNewTab: false}); "
            "</script>"
            "<style> .yasgui .autocompleteWrapper { visibility: hidden } .yasr .tableControls .tableFilter { margin-right: 10px; height: auto !important; } </style>"
            "</body>"
        )

    return head + body
