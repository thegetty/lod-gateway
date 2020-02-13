from re import findall
from os import environ
from datetime import datetime

from flask import Response, current_app


def generate_url(sub=[], base=False):
    """Create a URL string from relevant fragments

    Args:
        sub (list, optional): A list of additional URL parts
        base (bool, optional): Should the "activity-stream" part be added?

    Returns:
        String: The generated URL string
    """
    base_url = environ["LOD_BASE_URL"]
    namespace = current_app.config["NAMESPACE"]

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
        parts = findall("[A-Z][^A-Z]*", val)
        if parts and len(parts) > 0:
            # Lowercase each part of the val
            for index, part in enumerate(parts):
                parts[index] = part.lower()

            # Hyphenate the parts
            val = "-".join(parts)

    return val
