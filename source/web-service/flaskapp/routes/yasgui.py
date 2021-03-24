from flask import Blueprint, current_app

# Create a new "yasgui" route blueprint
yasgui = Blueprint("yasgui", __name__)

# ### ROUTES ###
@yasgui.route("/yasgui", methods=["GET"])
def get_yasgui():
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
        "</body>"
    )
    style = (
        "<style>"
        ".yasgui.autocompleteWrapper{display: none!important;}"
        ".yasr .tableControls .tableFilter {margin-right: 10px; height: 100%;}"
        "</style>"
    )

    return head + body + style
