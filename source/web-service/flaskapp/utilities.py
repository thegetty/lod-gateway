import copy
import json
import hashlib

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


def checksum_json(json_obj):
    # Expects a JSON-serializable data structure to be passed to it.
    checksum = hashlib.sha256()
    # dump the object as JSON, with the sort_keys flag on to ensure repeatability
    checksum.update(json.dumps(json_obj, sort_keys=True).encode("utf-8"))
    return checksum.hexdigest()


# Performs a recursive walkthrough of any dictionary/list calling the callback for any matched attribute
def containerRecursiveCallback(
    data, attr=None, find=None, replace=None, prefix=None, suffix=None, callback=None
):
    if not isinstance(data, (dict, list)):
        raise RuntimeError(
            "containerRecursiveCallback() The 'data' argument must be a dictionary or list type!"
        )

    if not (attr == None or (isinstance(attr, str) and len(attr) > 0)):
        raise RuntimeError(
            "containerRecursiveCallback() The 'attr' argument must be None or a non-empty string!"
        )

    data = copy.copy(data)

    def generalModify(key, value, find=None, replace=None, prefix=None, suffix=None):
        tmp = value

        if isinstance(find, str) and isinstance(replace, str):
            tmp = tmp.replace(find, replace)

        if isinstance(prefix, str) and len(prefix) > 0:
            tmp = prefix + tmp

        if isinstance(suffix, str) and len(suffix) > 0:
            tmp = tmp + suffix

        return tmp

    if callback == None:
        callback = generalModify

    if isinstance(data, dict):
        for key in data:
            val = data[key]

            if isinstance(val, (dict, list)):
                val = containerRecursiveCallback(
                    val,
                    attr=attr,
                    find=find,
                    replace=replace,
                    prefix=prefix,
                    suffix=suffix,
                    callback=callback,
                )
            else:
                if (attr == None or attr == key) and isinstance(val, str):
                    val = callback(
                        key,
                        val,
                        find=find,
                        replace=replace,
                        prefix=prefix,
                        suffix=suffix,
                    )

            data[key] = val
    elif isinstance(data, list):
        for key, val in enumerate(data):
            if isinstance(val, (dict, list)):
                val = containerRecursiveCallback(
                    val,
                    attr=attr,
                    find=find,
                    replace=replace,
                    prefix=prefix,
                    suffix=suffix,
                    callback=callback,
                )
            else:
                if (attr == None or attr == key) and isinstance(val, str):
                    val = callback(
                        key,
                        val,
                        find=find,
                        replace=replace,
                        prefix=prefix,
                        suffix=suffix,
                    )

            data[key] = val

    return data


def idPrefixer(attr, value, prefix=None, **kwargs):
    """Helper callback method to prefix non-prefixed JSON-LD document 'id' attributes"""

    temp = value

    if (
        (attr == "id")
        and (not (temp.startswith("http://") or temp.startswith("https://")))
        and (isinstance(prefix, str) and len(prefix) > 0)
    ):
        temp = prefix + "/" + temp

    return temp
