from rdflib import ConjunctiveGraph, Namespace


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
