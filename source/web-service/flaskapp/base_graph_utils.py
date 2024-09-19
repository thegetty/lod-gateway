from datetime import datetime
from functools import wraps

from flask import current_app

# To parse out the base graph
from pyld import jsonld

# docloader caching
import requests
from datetime import datetime, timedelta

from sqlalchemy.exc import ProgrammingError

from flaskapp.utilities import quads_to_triples, checksum_json
from flaskapp.storage_utilities.record import get_record, record_create

"""
Default base graph
------------------

Any triples that are recorded in the JSON-LD will be used as the set of triples to filter from other
documents. The named graph part of any quads will be discarded and replaced by the URI of the base
graph in the same way that 

Using named graphs in JSON-LD with @graph (https://www.w3.org/TR/json-ld11/#named-graphs) is a useful
container for triples that may or may not relate to one another.

For example:

{
    "@context": {
        "dc": "http://purl.org/dc/elements/1.1/",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "_label": {"@id": "rdfs:label"},
    },
    "@id": "_basegraph",
    "@graph": [
        {"@id": "urn:test1", "_label": "nothanks"},
        {"@id": "urn:test2", "_label": "nothanksagain"},
    ],
}

Here, the @graph container holds two unrelated triples which will be used for the filter: 

<urn:test1> <rdfs:label> "nothanks" .
<urn:test2> <rdfs:label> "nothanksagain" .

"""
DEFAULT_BASE_GRAPH = {
    "@id": None,
    "@type": "https://www.w3.org/2004/03/trix/rdfg-1/Graph",
    "_label": "Base Graph",
    "@graph": [],
}


# This is a custom document loader for PyLD - it allows us to set up a preloadable cache for contexts that are regularly retrieved.
# docCache format:
# {
#     "url": {
#         "expires": specific datetime, or None to never expire,
#         "document": context document, decoded from JSON,
#         "contextUrl": None,
#         "documentUrl": None,
#     }
# }
def document_loader(docCache, cache_expires=30):
    def load_document_and_cache(url, *args, **kwargs):
        now = datetime.now()
        if url in docCache:
            doc = docCache[url]
            expires = doc["expires"]
            if expires is not None:
                diff = now - expires
                if expires > now:
                    return doc
            else:
                # Expires: None - never expire
                return doc

        doc = {"expires": None, "contextUrl": None, "documentUrl": None, "document": ""}
        resp = requests.get(url)
        data = resp.json()
        doc["document"] = data
        doc["expires"] = now + timedelta(minutes=cache_expires)
        docCache[url] = doc
        return doc

    return load_document_and_cache


def base_graph_filter(basegraphobj, fqdn_id):
    try:
        record = get_record(basegraphobj)

        if record and record.data:
            # only change the named graph to be a FQDN
            data = dict(record.data)
        else:
            current_app.logger.warning(
                f"No base graph was present at {basegraphobj} - adding an empty base graph."
            )

            data = DEFAULT_BASE_GRAPH
            data["@id"] = basegraphobj

            record_create(data, commit=True)

        if "id" in data:
            data["id"] = fqdn_id
        elif "@id" in data:
            data["@id"] = fqdn_id

        proc = jsonld.JsonLdProcessor()
        serialized_nt = proc.to_rdf(
            data,
            {
                "format": "application/n-quads",
                "documentLoader": current_app.config["RDF_DOCLOADER"],
            },
        )
        serialized_nt = quads_to_triples(serialized_nt)

        return set((x.strip() for x in serialized_nt.split("\n") if x))

    except ProgrammingError as e:
        # Most likely the initial DB upgrade migration has not been run
        current_app.logger.critical(
            "Failed to access record table - has the initial flask db upgrade been run?"
        )
        return set()


# Not limiting the context cache, as there are typically only a few in play
# in most services. Even a hundred would be fine.
_PREFIX_CACHE = {}


def cache_context_prefixes(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if data := args[0]:
            strhash = checksum_json(data)
            dnow = datetime.timestamp(datetime.now())
            gap = dnow - current_app.config["CONTEXTPREFIX_TTL"]
            # If this context has not been resolved yet, or
            # if it has but the results are too old (older than the gap),
            # regenerate the result
            if (
                strhash not in _PREFIX_CACHE
                or _PREFIX_CACHE.get(strhash, [None, 0])[1] < gap
            ):
                _PREFIX_CACHE[strhash] = (f(*args, **kwargs), dnow)

            return _PREFIX_CACHE[strhash][0]
        return {}

    return wrapper


@cache_context_prefixes
def get_url_prefixes_from_context(context_json):
    # Get the list of mapped prefixes (eg 'rdfs') from the context
    proc = jsonld.JsonLdProcessor()
    options = {
        "isFrame": False,
        "keepFreeFloatingNodes": False,
        "documentLoader": current_app.config["RDF_DOCLOADER"],
        "extractAllScripts": False,
        "processingMode": "json-ld-1.1",
    }
    mappings = proc.process_context({"mappings": {}}, context_json, options)["mappings"]
    return {x for x in mappings if mappings[x]["_prefix"] == True}
