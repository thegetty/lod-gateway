import copy
import json
import hashlib
import traceback
import sys
import re

from datetime import datetime
from enum import Enum


# Enum with possible database events
# Used in 'ingest' and tests
class Event(Enum):
    Create = 1
    Update = 2
    Delete = 3
    Move = 4
    Refresh = 5


# Match quads only - doesn't handle escaped quotes yet, but the use of @graph JSON-LD will
# be specific to things like repeated triples and not general use. The regex could be  smarter
QUADS = re.compile(
    r"^(\<[^\>]*\>\s|_\:[A-z0-9]*\s){2}(_\:[A-z0-9]*|\<[^\>]*\>|\"(?:[^\"\\]|\\.)*\"(@[A-z]{1,4}|@[A-z]{1,4}-[A-z]{1,4}){0,1})(\^\^\<[^\>]*\>){0,1}\s(\<[^\>]*\>|_\:[A-z0-9]*)\s\.$"
)
NTRIPLES = re.compile(
    r"^(\<[^\>]*\>\s){2}(\<[^\>]*\>|\"(?:[^\"\\]|\\.)*\")(\^\^\<[^\>]*\>){0,1}\s\.$"
)


def is_quads(line):
    if line:
        if match := QUADS.match(line):
            return True
    return False


def is_ntriples(line):
    if line:
        if match := NTRIPLES.match(line):
            return True
    return False


def quads_to_triples(quads):
    return "\n".join(
        [
            (lambda l: f"{l.rsplit(' ', 2)[0]} ." if QUADS.match(l) is not None else l)(
                x
            )
            for x in quads.split("\n")
            if x.strip()
        ]
    )


def triples_to_quads(ntriples, namedgraph):
    return "\n".join(
        [
            (
                lambda l: (
                    f"{l.rsplit(' ', 1)[0]} <{namedgraph}> ."
                    if NTRIPLES.match(l) is not None
                    else l
                )
            )(x)
            for x in ntriples.split("\n")
            if x.strip()
        ]
    )


def graph_filter(ntriples, filterset):
    return "\n".join([x for x in ntriples.split("\n") if x not in filterset])


# gathers the full stack trace from the call site as a formatted string; useful for exception handling
# adapted from the answer here https://stackoverflow.com/a/16589622 by Tobias Kienzler
def full_stack_trace():
    exc = sys.exc_info()[0]

    # the last stack entry will be the call to full_stack_trace()
    stack = traceback.extract_stack()[:-1]

    # if an exception is present, remove the call to full_stack_trace()
    # as the printed exception will contain the caller instead
    if exc is not None:
        del stack[-1]

    tracestr = "Traceback (most recent call last):\n"

    stackstr = tracestr + "".join(traceback.format_list(stack))

    if exc is not None:
        stackstr += traceback.format_exc()[len(tracestr) :]

    return stackstr


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
    data,
    attr=None,
    find=None,
    replace=None,
    prefix=None,
    suffix=None,
    callback=None,
    recursive=True,
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
                if recursive == False:
                    continue

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
                if recursive == False:
                    continue

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

    # : is a reserved character for a URI and we shouldn't use them in
    # relative entity names either. Not prefixing if one is found
    if ":" not in temp and prefix:
        temp = prefix + "/" + temp

    return temp


def requested_linkformat(request_obj, default_response_type):
    # application/json or application/link-format preferred?
    # In cases where the client uses Accept: */*, the first item of the following
    # accept list will be returned, hence the repeat of 'default_response_type' there.
    return request_obj.accept_mimetypes.best_match(
        [default_response_type, "application/link-format", "application/json"],
        default=default_response_type,
    )


def wants_html(request_obj, default_response_type="text/html"):
    # application/json or application/link-format preferred?
    # In cases where the client uses Accept: */*, the first item of the following
    # accept list will be returned, hence the repeat of 'default_response_type' there.
    return request_obj.accept_mimetypes.best_match(
        [
            default_response_type,
            "text/html",
            "application/xhtml+xml",
            "application/xml",
            "application/json",
        ],
        default=default_response_type,
    ) in ["text/html", "application/xhtml+xml"]
