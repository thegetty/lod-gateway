import copy
import json
import hashlib
import traceback
import sys
import re
import requests

from enum import Enum

from flaskapp.errors import (
    status_wrong_auth_token,
    status_bad_auth_header,
    status_ok,
    status_nt,
    status_graphstore_error,
)


# Enum with possible database events
# Used in 'ingest' and tests
class Event(Enum):
    Create = 1
    Update = 2
    Delete = 3
    Move = 4
    Refresh = 5
    ContainerConflict = 6


# Match quads only - doesn't handle escaped quotes yet, but the use of @graph JSON-LD will
# be specific to things like repeated triples and not general use. The regex could be  smarter
QUADS = re.compile(
    r"^(\<[^\>]*\>\s|_\:[A-z0-9]*\s){2}(_\:[A-z0-9]*|\<[^\>]*\>|\"(?:[^\"\\]|\\.)*\"(@[A-z]{1,4}|@[A-z]{1,4}-[A-z]{1,4}){0,1})(\^\^\<[^\>]*\>){0,1}\s(\<[^\>]*\>|_\:[A-z0-9]*)\s\.$"
)
NTRIPLES = re.compile(
    r"^(\<[^\>]*\>\s){2}(\<[^\>]*\>|\"(?:[^\"\\]|\\.)*\")(\^\^\<[^\>]*\>){0,1}\s\.$"
)

# idPrefixer URI schemes it will not prefix with the LOD external URI on display
ALLOWED_SCHEMES = set(["https", "http", "ftp", "urn", "ftp", "file", "s3"])


def is_quads(line):
    if line:
        if _ := QUADS.match(line):
            return True
    return False


def is_ntriples(line):
    if line:
        if _ := NTRIPLES.match(line):
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
    urlprefixes=None,
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
                    urlprefixes=urlprefixes,
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
                        urlprefixes=urlprefixes,
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
                    urlprefixes=urlprefixes,
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
                        urlprefixes=urlprefixes,
                    )

            data[key] = val

    return data


def idPrefixer(attr, value, prefix=None, urlprefixes=None, **kwargs):
    """Helper callback method to prefix non-prefixed JSON-LD document 'id' attributes"""
    if urlprefixes is None:
        urlprefixes = set()

    joiner = "/" if not value.startswith("/") and not prefix.endswith("/") else ""

    if value.startswith("/") and prefix.endswith("/"):
        # two slashes, remove one
        value = value[1:]

    # prefix any relative uri with the prefix
    if value.split(":")[0] not in (ALLOWED_SCHEMES.union(urlprefixes)) and prefix:
        return prefix + joiner + value

    return value


def idUnPrefixer(attr, value, prefix="", **kwargs):
    """Helper callback method to remove the prefix from JSON-LD document 'id' attributes"""
    if prefix and not prefix.endswith("/"):
        prefix = f"{prefix}/"
    return value.removeprefix(prefix)


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
            "application/ld+json",
            "application/rdf+xml",
            "text/turtle",
            "text/n-triples",
            "text/n-quads",
        ],
        default=default_response_type,
    ) in ["text/html", "application/xhtml+xml"]


# ### AUTHENTICATION FUNCTIONS ###
def authenticate_bearer(request, current_app):
    # For now return the same error for all failing scenarios
    error = status_wrong_auth_token

    # Get Authorization header token
    auth_header = request.headers.get("Authorization")

    # Return error if auth header is not present
    if not auth_header:
        return error

    else:
        # get method (Bearer) and token
        try:
            method, token = auth_header.split(maxsplit=1)
        except ValueError:
            return status_bad_auth_header

        # check the method is correct
        if method != "Bearer":
            return error

        # verify token
        elif token != current_app.config["AUTH_TOKEN"]:
            return error

    return status_ok


def execute_sparql_query(query: str, accept_header: str, query_endpoint: str):
    try:
        res = requests.post(
            query_endpoint, data={"query": query}, headers={"Accept": accept_header}
        )

        res.raise_for_status()

        return res.content
    except requests.exceptions.HTTPError as e:
        response = status_nt(res.status_code, type(e).__name__, str(res.content))
        return response
    except requests.exceptions.ConnectionError:
        return status_graphstore_error


def execute_sparql_query_post(data: dict, accept_header: str, query_endpoint: str):
    try:
        res = requests.post(
            query_endpoint, data=data, headers={"Accept": accept_header}
        )
        res.raise_for_status()

        return res
    except requests.exceptions.HTTPError as e:
        response = status_nt(res.status_code, type(e).__name__, str(res.content))
        return response
    except requests.exceptions.ConnectionError:
        return status_graphstore_error


# entity_id -> container chain then entity
def segment_entity_id(entity_id):
    segments = []
    # clean up
    seq = [x for x in entity_id.split("/") if x]
    clean_entity_id = "/" + "/".join(seq)
    if not entity_id.endswith("/"):
        seq = seq[:-1]
    else:
        clean_entity_id += "/"
    seq = [x for x in seq if x]
    for segment in seq:
        if segments:
            segments.append(f"{segments[-1]}{segment}/")
        else:
            segments.append(f"/{segment}/")
    segments = ["/"] + segments
    if segments[-1] != clean_entity_id:
        segments.append(clean_entity_id)
    return segments
