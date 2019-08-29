import os
import json, re, requests, rdflib
from pyld import jsonld

from app.utilities import has, get, sprintf, debug

neptune_endpoint = os.getenv("MART_NEPTUNE_ENDPOINT", None)


class GraphStore:
    def __init__(self):
        debug("GraphStore.__init__() called...", level=1)

        self.connection = None

        self.configuration = {
            "hostname": os.getenv("MART_NEPTUNE_HOST", None),
            "hostport": os.getenv("MART_NEPTUNE_PORT", None),
            "endpoint": os.getenv("MART_NEPTUNE_ENDPOINT", None),
            "graphname": os.getenv("MART_NEPTUNE_GRAPH", None),
            "username": os.getenv("MART_NEPTUNE_USERNAME", None),
            "password": os.getenv("MART_NEPTUNE_PASSWORD", None),
        }

        debug("GraphStore.__init__() configuration = %o", self.configuration, level=2)

    @staticmethod
    def update(graph_id, namespace, json_data):
        try:
            graph_name = (
                "http://data.getty.edu/" + namespace + "/" + graph_id + "-graph"
            )

            debug("GraphStore.update(entity: %s) called..." % (graph_name), level=0)

            json_obj = json.loads(json_data)
            expanded = jsonld.expand(json_obj)
            g = rdflib.ConjunctiveGraph()
            g.parse(data=json.dumps(expanded), format="json-ld")
            serialized_nt = g.serialize(format="nt").decode("UTF-8")

            # delete graph if it exists
            GraphStore.delete(graph_id, namespace)

            # insert graph
            insert_stmt = (
                "INSERT DATA {GRAPH <" + graph_name + "> {" + serialized_nt + "}}"
            )
            res = requests.post(neptune_endpoint, data={"update": insert_stmt})
            if res.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            debug(
                "GraphStore.update() problem found with record %s, error: %s"
                % (graph_name, str(e)),
                error=True,
            )
            return False

    @staticmethod
    def delete(graph_id, namespace):
        graph_name = "http://data.getty.edu/" + namespace + "/" + graph_id + "-graph"

        debug("GraphStore.delete(entity: %s) called..." % (graph_name), level=0)

        # check to see if graph exists
        res = requests.post(
            neptune_endpoint,
            data={
                "query": "SELECT (count(?s) as ?count) { GRAPH <"
                + graph_name
                + "> {?s ?p ?o}}"
            },
        )
        count_json = json.loads(res.content)
        if int(count_json["results"]["bindings"][0]["count"]["value"]) > 0:
            # drop graph
            res = requests.post(
                neptune_endpoint, data={"update": "DROP GRAPH <" + graph_name + ">"}
            )
            if res.status_code == 200:
                return True
            else:
                return False

