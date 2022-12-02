import re

from flaskapp.models import db
from flaskapp.models.record import Record

# To parse out the base graph
from pyld import jsonld

# Match quads only - doesn't handle escaped quotes yet, but the use of @graph JSON-LD will
# be specific to things like repeated triples and not general use. The regex could be  smarter
QUADS = re.compile(
    r"^(\<[^\>]*\>\s){2}(\<[^\>]*\>|\"(?:[^\"\\]|\\.)*\")\s\<[^\>]*\>\s\.$"
)


def is_quads(line):
    if line:
        if match := QUADS.match(line):
            return True

    return False


def quads_to_triples(quads):
    return "\n".join(
        [f"{x.rsplit(' ', 2)[0]} ." for x in quads.split("\n") if x.strip()]
    )


def base_graph_filter(basegraphobj, fqdn_id):
    record = (
        db.session.query(Record).filter(Record.entity_id == basegraphobj).one_or_none()
    )
    if record and record.data:
        # only change the named graph to be a FQDN
        data = dict(record.data)
        if "id" in data:
            data["id"] = fqdn_id
        elif "@id" in data:
            data["@id"] = fqdn_id

        proc = jsonld.JsonLdProcessor()
        serialized_nt = proc.to_rdf(data, {"format": "application/n-quads"})
        if is_quads(serialized_nt.split("\n")[0]):
            serialized_nt = quads_to_triples(serialized_nt)

        return set((x.strip() for x in serialized_nt.split("\n") if x))
    else:
        return


def graph_filter(ntriples, filterset):
    return "\n".join([x for x in ntriples.split("\n") if x not in filterset])
