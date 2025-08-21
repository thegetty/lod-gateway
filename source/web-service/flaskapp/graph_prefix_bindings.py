from rdflib import ConjunctiveGraph, Namespace

from rdflib.namespace import DC, DCTERMS


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
    "application/n-triples; charset=UTF-8": "nt11",
    "application/ntriples; charset=UTF-8": "nt11",
    "text/turtle; charset=UTF-8": "turtle",
    "application/rdf+xml; charset=UTF-8": "xml",
    "text/n3; charset=UTF-8": "n3",
    # RDF Quad/Triple formats:
    "application/n-quads; charset=UTF-8": "nquads",
    "application/nquads; charset=UTF-8": "nquads",
    "application/ld+json; charset=UTF-8": "json-ld",
    "application/trig; charset=UTF-8": "trig",
    # "application/trix;charset=UTF-8": "trix",        the TriX output is not great tbh
}


def get_bound_graph(identifier):
    g = ConjunctiveGraph(identifier=identifier)
    g.bind("dc", DC)
    g.bind("dcterm", DCTERMS)
    for k, v in BINDING.items():
        g.bind(k, v)
    return g
