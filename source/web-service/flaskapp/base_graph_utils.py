from flaskapp.models import db
from flaskapp.models.record import Record

from flask import current_app

# To parse out the base graph
from pyld import jsonld

from sqlalchemy.exc import ProgrammingError

from flaskapp.utilities import is_quads, quads_to_triples
from flaskapp.storage_utilities.record import get_record, record_create


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
            data = {
                "@id": basegraphobj,
                "@type": "https://www.w3.org/2004/03/trix/rdfg-1/Graph",
                "_label": "Base Graph",
                "@graph": [],
            }
            record_create(data, commit=True)

        if "id" in data:
            data["id"] = fqdn_id
        elif "@id" in data:
            data["@id"] = fqdn_id

        proc = jsonld.JsonLdProcessor()
        serialized_nt = proc.to_rdf(data, {"format": "application/n-quads"})
        if is_quads(serialized_nt.split("\n")[0]):
            serialized_nt = quads_to_triples(serialized_nt)

        return set((x.strip() for x in serialized_nt.split("\n") if x))

    except ProgrammingError as e:
        # Most likely the initial DB upgrade migration has not been run
        current_app.logger.critical(
            "Failed to access record table - has the initial flask db upgrade been run?"
        )
        return set()
