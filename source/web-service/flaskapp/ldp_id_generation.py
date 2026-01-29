from uuid import uuid4


def _get_uuid():
    return str(uuid4())


# This can be extended to include other mechanisms for generating identifiers for
# RDF named graphs POSTed to LDP containers, such as getting a short ID from an IDM for example


LDP_ID_GEN_OPTIONS = {"uuid": _get_uuid}
