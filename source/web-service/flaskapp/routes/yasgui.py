from flask_openapi3 import APIBlueprint
from flask import current_app, abort
from flaskapp.errors import status_nt, construct_error_response
from flaskapp.openapi import sparql_tag

# Create a new "yasgui" route blueprint
yasgui = APIBlueprint("yasgui", __name__)

_OPENAPI_KWARGS = frozenset(
    [
        "tags",
        "summary",
        "responses",
        "description",
        "security",
        "deprecated",
        "external_docs",
        "servers",
        "operation_id",
        "openapi_extensions",
    ]
)


_original_yasgui_add_url_rule = yasgui.add_url_rule


def _yasgui_add_url_rule(*args, **kwargs):
    for key in _OPENAPI_KWARGS:
        kwargs.pop(key, None)
    _original_yasgui_add_url_rule(*args, **kwargs)


yasgui.add_url_rule = _yasgui_add_url_rule


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
    yasgui_page = create_yasgui_html(endpoint)
    return yasgui_page


def create_yasgui_html(endpoint):
    head = (
        "<head>"
        "<link href='https://unpkg.com/@triply/yasgui/build/yasgui.min.css' rel='stylesheet' type='text/css' />"
        "<script src='https://unpkg.com/@triply/yasgui/build/yasgui.min.js'></script>"
        "</head>"
    )
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
