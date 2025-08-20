import re
import requests

from werkzeug.http import parse_accept_header

# type hint imports
from flask import Request
from gettysparqlpatterns import PatternSet

from flaskapp.errors import status_graphstore_error, status_nt

from .graph_prefix_bindings import FORMATS

# Trying to use a regex to parse out a profile="" statement from the Accept header
# Not in use yet, but is close to workable so keeping this here.
ACCEPT_PROFILE_REGEX = re.compile(
    r"""(?P<profilemimetype>[^;]*)\;\s*profile="(?P<profile>[^"]+)"|(?P<mimetype>^[-\\
w.]+\/[-\w\+]+$)"""
)


def desired_rdf_format(accept: str, accept_param: str) -> tuple[str, str] | None:
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


def desired_rdf_mimetype_from_format(
    format_param: str, q: float = 1.0
) -> tuple[str, str | float, str]:
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
    accepted_mimetypes = None

    mediatype = None
    # either the content of _mediatype, or whatever is left in mediatype based on 'format'
    if mediatype := request.args.get("_mediatype") or request.args.get("format"):
        accepted_mimetypes = [desired_rdf_mimetype_from_format(mediatype, 1.0)]

    # if the proposed mediatype/format did NOT result in any acceptable mimetypes, check the accept header
    if not accepted_mimetypes:
        # Use the Accept header and generate a sorted list of acceptables.
        # This path will likely be from a browser request.
        accept_header = request.headers.get("Accept", "*/*")
        # The werkzeug parse function is quite hardened, so it's not going to throw exceptions on bad data
        accepted_mimetypes = [
            desired_rdf_mimetype_from_format(mimetype, float(q))
            for mimetype, q in parse_accept_header(accept_header)
        ]
        # Still couldn't find anything?
        if not accepted_mimetypes:
            accepted_mimetypes = [
                ("application/ld+json; charset=UTF-8", 1.0, "json-ld")
            ]

    # Only accept mimetypes that can be mapped to a RDF transformable format
    accepted_mimetypes = [
        x
        for x in sorted(accepted_mimetypes, key=lambda item: item[1], reverse=True)
        if x[2] != ""
    ]

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


def return_pattern_for_profile(
    uritype: str, profiles: str, patterns: dict
) -> PatternSet | None:
    # No possible patterns for this uritype
    if uritype not in patterns:
        return None
    p_list = [x[0] for x in profiles]
    for pattern in patterns[uritype]:
        if pattern.profile_uri in p_list:
            return pattern


def get_data_using_profile_query(
    uri: str,
    uritype: str,
    profiles: str,
    patterns: dict,
    query_endpoint: str,
    accept_header: str = "application/ld+json, text/turtle",
) -> tuple[str, str, str] | None:
    # Returns the content and returned mimetype from the SPARQL construct query verbatim
    # Returns None if no matching pattern can be used or found
    # Raises error if one is hit
    if pattern := return_pattern_for_profile(uritype, profiles, patterns):
        profile = pattern.profile_uri
        sparql_query = pattern.get_query(URI=uri)
        try:
            res = requests.post(
                query_endpoint,
                data={"query": sparql_query},
                headers={"Accept": accept_header},
            )
            res.raise_for_status()

            if res.content:
                return res.content, res.headers.get("Content-Type"), profile
            else:
                return status_nt(
                    500,
                    "Empty response from Profile Generation",
                    f"Used query: '{sparql_query}', got blank response back.",
                )
        except requests.exceptions.HTTPError as e:
            return status_nt(res.status_code, type(e).__name__, str(res.content))
        except requests.exceptions.ConnectionError:
            return status_graphstore_error
        except Exception as e:
            print(f"Hit unexpected Exception {str(e)}")
            raise e
