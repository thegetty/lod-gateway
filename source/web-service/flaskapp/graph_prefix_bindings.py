import re
from rdflib import ConjunctiveGraph, Namespace
from werkzeug.http import parse_accept_header

# type hint imports
from flask import Request

BINDING = {
    "crm": Namespace("http://www.cidoc-crm.org/cidoc-crm/"),
    "aat": Namespace("http://vocab.getty.edu/aat/"),
    "sci": Namespace("http://www.ics.forth.gr/isl/CRMsci/"),
    "schema": Namespace("http://schema.org/"),
    "dig": Namespace("http://www.ics.forth.gr/isl/CRMdig/"),
    "la": Namespace("https://linked.art/ns/terms/"),
    "archaeo": Namespace("http://www.cidoc-crm.org/cidoc-crm/CRMarchaeo/"),
    "as": Namespace("https://www.w3.org/ns/activitystreams#"),
    "ldp": Namespace("http://www.w3.org/ns/ldp#"),
    "vcard": Namespace("http://www.w3.org/2006/vcard/ns#"),
    "oa": Namespace("http://www.w3.org/ns/oa#"),
    "owl": Namespace("http://www.w3.org/2002/07/owl#"),
    "prov": Namespace("http://www.w3.org/ns/prov#"),
}

FORMATS = {
    # RDF triple formats
    "application/ntriples;charset=UTF-8": "nt11",
    "text/turtle;charset=UTF-8": "turtle",
    "application/rdf+xml;charset=UTF-8": "xml",
    "text/n3;charset=UTF-8": "n3",
    # RDF Quad/Triple formats:
    "application/n-quads;charset=UTF-8": "nquads",
    "application/ld+json;charset=UTF-8": "json-ld",
    "application/trig;charset=UTF-8": "trig",
    # "application/trix;charset=UTF-8": "trix",        the TriX output is not great tbh
}

ACCEPT_PROFILE_REGEX = re.compile(
    r"""(?P<profilemimetype>[^;]*)\;\s*profile="(?P<profile>[^"]+)"|(?P<mimetype>^[-\\
w.]+\/[-\w\+]+$)"""
)


def get_bound_graph(identifier):
    g = ConjunctiveGraph(identifier=identifier)
    for k, v in BINDING.items():
        g.bind(k, v)
    return g


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
        if format_param == "nt":
            format_param = "nt11"
        for k, v in FORMATS.items():
            if v == format_param.strip() or k.startswith(format_param.split(";")[0]):
                return (k, q, v)
    # Not a shorthand value like 'nt', 'turtle', etc? Just return what's given:
    return (format_param, q, "")


def determine_requested_format_and_profile(request: Request) -> dict:
    # RDF format importance: _mediatype >= format > Accept header
    # set the default response mimetype:
    accepted_mimetypes = [("application/ld+json;charset=UTF-8", 1.0, "json-ld")]

    mediatype = None
    # either the content of _mediatype, or whatever is left in mediatype based on 'format'
    if mediatype := request.args.get("_mediatype") or request.args.get("format"):
        accepted_mimetypes = [desired_rdf_mimetype_from_format(mediatype)]
    else:
        # Use the Accept header and generate a sorted list of acceptables.
        # This path will likely be from a browser request.
        accept_header = request.headers.get("Accept", "*/*")
        # The werkzeug parse function is quite hardened, so it's not going to throw exceptions on bad data
        accepted_mimetypes = [
            desired_rdf_mimetype_from_format(mimetype, q)
            for mimetype, q in parse_accept_header(accept_header)
        ]

    # After working out what sort of RDF response is necessary, is there a profile?
    # Priority: _profile > Accept-Profile > Profile
    if profile := request.args.get("_profile"):
        profiles = [profile]
    else:
        accept_profile_header = request.headers.get("Accept-Profile")
        profile_header = request.headers.get("Profile")
        if accept_profile_header:
            profiles = [p.strip() for p in accept_profile_header.split(",")]
        elif profile_header:
            profiles = [profile_header.strip()]
        else:
            profiles = []

    return {
        "preferred_mimetype": accepted_mimetypes[0][0] if accepted_mimetypes else None,
        "accepted_mimetypes": [m[0] for m in accepted_mimetypes],
        "requested_profiles": profiles,
    }
