from rdflib import ConjunctiveGraph, Namespace


BINDING = {
    "crm": "http://www.cidoc-crm.org/cidoc-crm/",
    "aat": "http://vocab.getty.edu/aat/",
    "sci": "http://www.ics.forth.gr/isl/CRMsci/",
    "schema": "http://schema.org/",
    "dig": "http://www.ics.forth.gr/isl/CRMdig/",
    "la": "https://linked.art/ns/terms/",
    "archaeo": "http://www.cidoc-crm.org/cidoc-crm/CRMarchaeo/",
    "as": "https://www.w3.org/ns/activitystreams#",
    "ldp": "http://www.w3.org/ns/ldp#",
    "vcard": "http://www.w3.org/2006/vcard/ns#",
    "oa": "http://www.w3.org/ns/oa#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "prov": "http://www.w3.org/ns/prov#",
}

FORMATS = {
    "applicaton/ntriples": "nt",
    "text/turtle": "turtle",
    "application/rdf+xml": "xml",
    "application/ld+json": "json-ld",
    "text/n3": "n3",
    "application/n-quads": "nquads",
}


def get_bound_graph(identifier):
    g = ConjunctiveGraph(identifier=identifier)
    for k, v in BINDING.items():
        g.bind(k, Namespace(v))
    return g


def desired_rdf_format(accept, accept_param):
    if accept_param:
        for k, v in FORMATS.items():
            if v == accept_param.strip():
                return (k, v)
    if accept:
        for k, v in FORMATS.items():
            if k in accept:
                return (k, v)
