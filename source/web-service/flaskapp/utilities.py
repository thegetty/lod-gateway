import os
import re

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


def camel_case(val):
    if isinstance(val, str) and len(val) > 0:
        parts = val.split("-")
        if len(parts) > 0:
            for index, part in enumerate(parts):
                parts[index] = part.lower().capitalize()

            val = "".join(parts)

    return val


def uncamel_case(val):
    if isinstance(val, str) and len(val) > 0:
        # Split the val on uppercase characters
        parts = re.findall("[A-Z][^A-Z]*", val)
        if parts and len(parts) > 0:
            # Lowercase each part of the val
            for index, part in enumerate(parts):
                parts[index] = part.lower()

            # Hyphenate the parts
            val = "-".join(parts)

    return val
