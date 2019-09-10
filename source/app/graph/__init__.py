import os
import json
import re
import requests
import rdflib

from pyld import jsonld

from app.utilities import has, get, sprintf, debug

class GraphStore:
    def __init__(self):
        debug("GraphStore.__init__() called...", level=1)

        self.configuration = {
            "endpoint": os.getenv("MART_NEPTUNE_ENDPOINT", None),
            "username": os.getenv("MART_NEPTUNE_USERNAME", None),
            "password": os.getenv("MART_NEPTUNE_PASSWORD", None),
        }
        
        debug("GraphStore.__init__() configuration = %o", self.configuration, level=2)

    @staticmethod
    def update(entityURI, jsonData):
        try:
            graphName = (
                entityURI + "-graph"
            )

            debug("GraphStore.update(entity: %s) called..." % (graphName), level=0)
            
            jsonObj  = json.loads(jsonData)
            expanded = jsonld.expand(jsonObj)
            
            graph = rdflib.ConjunctiveGraph()
            graph.parse(data=json.dumps(expanded), format="json-ld")
            
            serializedNT = graph.serialize(format="nt").decode("UTF-8")
            
            # delete graph if it exists
            GraphStore.delete(entityURI)
            
            # insert graph
            insertStatement = (
                "INSERT DATA {GRAPH <" + graphName + "> {" + serializedNT + "}}"
            )
            
            response = requests.post(
                self.configuration["endpoint"],
                data={
                    "update": insertStatement,
                })
            
            if(response.status_code == 200):
                return True
            else:
                return False
        except Exception as e:
            debug(
                "GraphStore.update() problem found with record %s, error: %s"
                % (graphName, str(e)),
                error=True,
            )
            
            return False

    @staticmethod
    def delete(entityURI):
        graphName = entityURI + "-graph"
        
        debug("GraphStore.delete(entity: %s) called..." % (graphName), level=0)
        
        # check to see if graph exists
        response = requests.post(
            self.configuration["endpoint"],
            data={
                "query": "SELECT (count(?s) as ?count) { GRAPH <"
                + graphName
                + "> {?s ?p ?o}}"
            },
        )
        
        if(response.status_code == 200):
            countObj = json.loads(response.content)
            if(countObj):
                if(int(countObj["results"]["bindings"][0]["count"]["value"]) > 0):
                    # drop graph
                    response = requests.post(
                        self.configuration["endpoint"],
                        data={
                            "update": "DROP GRAPH <" + graphName + ">"
                        }
                    )

                    if(response.status_code == 200):
                        return True
        
        return False
