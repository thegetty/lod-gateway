import os

from flask import Response, current_app
from datetime import datetime


def error_response(error):
    """Construct a error message.

    TODO: Evaluate if this is actually needed, or if we can just use the standard method

    Args:
        error (Tuple): (error core, error message)

    Returns:
        Response: A error message
    """
    return Response(error[1], status=error[0], headers={"X-Error": error[1]})


def validate_namespace(namespace):
    """Ensure that each call has a namespace, returning the default if needed

    Args:
        namespace (String): The namespace to test

    Returns:
        String: The provided namespace, or the default if none provided
    """
    if not namespace:
        namespace = current_app.config["DEFAULT_URL_NAMESPACE"]
    return namespace


def generate_url(namespace=None, sub=[], base=False):
    """Create a URL string from relevant fragments

    Args:
        namespace (String, optional): A namespace for the URL
        sub (list, optional): A list of additional URL parts
        base (bool, optional): Should the "activity-stream" part be added?

    Returns:
        String: The generated URL string
    """
    base_url = os.getenv("LOD_BASE_URL", "")

    if base:
        as_prefix = None
    else:
        as_prefix = "activity-stream"

    parts = [base_url, namespace, as_prefix, "/".join(sub)]
    parts = [item for item in parts if item]
    return "/".join(parts)


def format_datetime(dt):
    if isinstance(dt, datetime):
        formatted = dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        if isinstance(formatted, str) and len(formatted) > 0:
            formatted = formatted[:-2] + ":" + formatted[-2:]
            return formatted

    return None
