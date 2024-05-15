from flask import Blueprint, current_app, abort
from flaskapp.errors import status_nt, construct_error_response

# Create a new "yasgui" route blueprint
yasgui = Blueprint("yasgui", __name__)


# ### ROUTES ###
@yasgui.route("/sparql-ui", methods=["GET"])
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
