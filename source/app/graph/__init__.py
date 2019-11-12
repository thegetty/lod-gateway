import os
import json
import re
import requests
import rdflib

from pyld import jsonld

from app.di import DI

from app.utilities import has, get, sprintf, debug


class GraphStore:

    configuration = {
        "host": os.getenv("NEPTUNE_HOST", None),
        "port": os.getenv("NEPTUNE_PORT", None),
    }

    @classmethod
    def enabled(cls):
        # Support for toggling Neptune during runtime for certain configurations
        config = DI.get("config")
        if isinstance(config, dict):
            enabled = get(config, "neptune.enabled")
            if isinstance(enabled, bool):
                return enabled

        # Determine enabled status based on environment variable
        return os.getenv("NEPTUNE_ENABLED", "YES") == "YES"

    @classmethod
    def endpoint(cls):
        if not (
            isinstance(cls.configuration["host"], str)
            and len(cls.configuration["host"]) > 0
        ):
            raise RuntimeError(
                "No valid Amazon Neptune instance hostname has been specified! Please review application configuration and try again!"
            )

        endpoint = cls.configuration["host"]

        if (
            isinstance(cls.configuration["port"], str)
            and len(cls.configuration["port"]) > 0
        ):
            endpoint += ":" + cls.configuration["port"]

        return sprintf("http://%s/sparql" % (endpoint))

    @classmethod
    def query(cls, query):
        debug("GraphStore.query(query: %s) called..." % (query), level=1)

        if not cls.enabled():
            debug(
                "GraphStore.query(query: %s) graph store access disabled via configuration, returning immediately..."
                % (query),
                level=2,
            )
            return True

        try:
            # check to see if graph exists
            response = requests.post(cls.endpoint(), data={"query": query,},)

            if response.status_code == 200:
                content = json.loads(response.content)
                if content:
                    return content
            else:
                debug(
                    "GraphStore.query() Failed! HTTP Response Status Code: %d"
                    % (response.status_code),
                    error=True,
                )
                if response.content:
                    debug(response.content)

        except Exception as e:
            debug("GraphStore.query() error: %s" % (str(e)), error=True)

            return False

    @classmethod
    def select(cls, entityURI):
        debug("GraphStore.select(URI: %s) called..." % (entityURI), level=1)

        if not cls.enabled():
            debug(
                "GraphStore.select(URI: %s) graph store access disabled via configuration, returning immediately..."
                % (entityURI),
                level=2,
            )
            return True

        try:
            graphName = entityURI + "-graph"

            # check to see if graph exists
            response = requests.post(
                cls.endpoint(),
                data={
                    "query": "SELECT (count(?s) as ?count) { GRAPH <"
                    + graphName
                    + "> {?s ?p ?o}}"
                },
            )

            if response.status_code == 200:
                countObj = json.loads(response.content)
                if countObj:
                    if int(countObj["results"]["bindings"][0]["count"]["value"]) > 0:
                        return True

        except Exception as e:
            debug(
                "GraphStore.select() %s, error: %s" % (graphName, str(e)), error=True,
            )

            return False

    @classmethod
    def update(cls, entityURI, jsonData):
        debug("GraphStore.update(URI: %s) called..." % (entityURI), level=1)

        if not cls.enabled():
            debug(
                "GraphStore.update(URI: %s) graph store access disabled via configuration, returning immediately..."
                % (entityURI),
                level=2,
            )
            return True

        try:
            graphName = entityURI + "-graph"

            debug("GraphStore.update(URI: %s) called..." % (graphName), level=0)

            jsonObj = json.loads(jsonData)
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

            response = requests.post(cls.endpoint(), data={"update": insertStatement,})

            if response.status_code == 200:
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

    @classmethod
    def delete(cls, entityURI):
        debug("GraphStore.delete(URI: %s) called..." % (entityURI), level=1)

        if not cls.enabled():
            debug(
                "GraphStore.delete(URI: %s) graph store access disabled via configuration, returning immediately..."
                % (entityURI),
                level=2,
            )
            return True

        graphName = entityURI + "-graph"

        # check to see if graph exists
        response = requests.post(
            cls.endpoint(),
            data={
                "query": "SELECT (count(?s) as ?count) { GRAPH <"
                + graphName
                + "> {?s ?p ?o}}"
            },
        )

        if response.status_code == 200:
            countObj = json.loads(response.content)
            if countObj:
                if int(countObj["results"]["bindings"][0]["count"]["value"]) > 0:
                    # drop graph
                    response = requests.post(
                        cls.endpoint(),
                        data={"update": "DROP GRAPH <" + graphName + ">"},
                    )

                    if response.status_code == 200:
                        return True

        return False
