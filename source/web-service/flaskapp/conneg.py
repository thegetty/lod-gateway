import re

from werkzeug.http import parse_accept_header

# type hint imports
from flask import Request

from .graph_prefix_bindings import FORMATS

# Trying to use a regex to parse out a profile="" statement from the Accept header
# Not in use yet, but is close to workable so keeping this here.
ACCEPT_PROFILE_REGEX = re.compile(
    r"""(?P<profilemimetype>[^;]*)\;\s*profile="(?P<profile>[^"]+)"|(?P<mimetype>^[-\\
w.]+\/[-\w\+]+$)"""
)


def desired_rdf_format(accept, accept_param):
    if accept_param:
        if accept_param == "nt":
            accept_param = "nt11"
        for k, v in FORMATS.items():
            if v == accept_param.strip():
                return (k, v)
    if accept:
        for k, v in FORMATS.items():
            if k in accept:
                return (k, v)


def desired_rdf_mimetype_from_format(format_param: str, q: float = 1.0) -> str:
    if format_param:
        if format_param in ["*", "*/*"]:
            format_param = "json-ld"
        if format_param == "nt":
            format_param = "nt11"
        for k, v in FORMATS.items():
            if v == format_param.strip():
                return (k, q, v)
            elif k.split(";")[0] == format_param.split(";")[0]:
                return (format_param, q, v)
    # Not a shorthand value like 'nt', 'turtle', etc? Just return what's given:
    return (format_param, q, "")


def determine_requested_format_and_profile(request: Request) -> dict:
    # RDF format importance: _mediatype >= format > Accept header
    # set the default response mimetype:
    accepted_mimetypes = [("application/ld+json; charset=UTF-8", 1.0, "json-ld")]

    mediatype = None
    # either the content of _mediatype, or whatever is left in mediatype based on 'format'
    if mediatype := request.args.get("_mediatype") or request.args.get("format"):
        accepted_mimetypes = [desired_rdf_mimetype_from_format(mediatype, 1.0)]
    else:
        # Use the Accept header and generate a sorted list of acceptables.
        # This path will likely be from a browser request.
        accept_header = request.headers.get("Accept", "*/*")
        # The werkzeug parse function is quite hardened, so it's not going to throw exceptions on bad data
        accepted_mimetypes = [
            desired_rdf_mimetype_from_format(mimetype, float(q))
            for mimetype, q in parse_accept_header(accept_header)
        ]

    accepted_mimetypes = sorted(
        accepted_mimetypes, key=lambda item: item[1], reverse=True
    )

    # After working out what sort of RDF response is necessary, is there a profile?
    # Priority: _profile > Accept-Profile > Profile
    if profile := request.args.get("_profile"):
        profiles = [(profile, 1)]
    else:
        accept_profile_header = request.headers.get("Accept-Profile")
        if accept_profile_header:
            # Same rough format as the Accept header. Parse and sort by q value
            profiles = parse_accept_header(accept_profile_header)
            profiles = sorted(profiles, key=lambda item: item[1], reverse=True)
        else:
            profiles = []

    return {
        "preferred_mimetype": accepted_mimetypes[0][0] if accepted_mimetypes else None,
        "accepted_mimetypes": accepted_mimetypes,
        "requested_profiles": profiles,
    }
