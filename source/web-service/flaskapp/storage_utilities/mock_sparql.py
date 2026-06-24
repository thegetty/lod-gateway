"""
In-memory RDFLib-based SPARQL mock service.

Replaces the requests_mock-based approach with a real RDFLib graph that
accepts SPARQL UPDATE statements (INSERT DATA, DROP GRAPH, etc.) and
executes SPARQL SELECT/CONSTRUCT queries against stored data.
"""

from __future__ import annotations

import io
import json
import re
from typing import Any, Dict, Optional

import rdflib
from rdflib import URIRef
from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer


def _serialize_sparql_json(results) -> str:
    """Serialize SPARQL query results to JSON format."""
    out = io.StringIO()
    JSONResultSerializer(results).serialize(out)
    return out.getvalue()


class MockSPARQLService:
    """In-memory SPARQL endpoint backed by an RDFLib ConjunctiveGraph."""

    RDFLIB = rdflib

    def __init__(self) -> None:
        self.graph = self.RDFLIB.ConjunctiveGraph()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_request(
        self,
        path: str,
        body: Optional[str],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Route an incoming request and return a dict with keys:
            status_code  (int)
            body         (str or bytes)
            headers      (dict)
        """
        if path.endswith("/status"):
            return self._handle_status()
        if path.endswith("/sparql"):
            return self._handle_sparql(body, headers or {})
        if path.endswith("/update"):
            return self._handle_update(body)
        return {"status_code": 400, "body": None, "headers": {}}

    # ------------------------------------------------------------------
    # /status
    # ------------------------------------------------------------------

    def _handle_status(self) -> Dict[str, Any]:
        return {
            "status_code": 200,
            "body": json.dumps({"status": "healthy"}),
            "headers": {"Content-Type": "application/json"},
        }

    # ------------------------------------------------------------------
    # /sparql  (queries only)
    # ------------------------------------------------------------------

    def _handle_sparql(
        self, body: Optional[str], headers: Dict[str, str]
    ) -> Dict[str, Any]:
        query = self._extract_query_param(body) if body else None

        if not query:
            return {"status_code": 400, "body": None, "headers": {}}

        accept = (headers.get("Accept") or "application/json").split(",")[0].strip()

        try:
            upper = query.strip().upper()
            if upper.startswith("SELECT"):
                return self._exec_select(query, accept)
            if upper.startswith("CONSTRUCT"):
                return self._exec_construct(query, accept)
            if upper.startswith("ASK"):
                return self._exec_ask(query, accept)
            if upper.startswith("DESCRIBE"):
                return self._exec_describe(query, accept)
        except Exception as exc:
            return {
                "status_code": 500,
                "body": str(exc),
                "headers": {"Content-Type": "text/plain"},
            }

        return {"status_code": 400, "body": None, "headers": {}}

    def _exec_select(
        self, query: str, accept: str
    ) -> Dict[str, Any]:
        results = self.graph.query(query)
        accept_lower = accept.lower()

        if "json" in accept_lower:
            body = _serialize_sparql_json(results)
            return {
                "status_code": 200,
                "body": body,
                "headers": {"Content-Type": "application/sparql-results+json"},
            }
        if "xml" in accept_lower:
            body = results.serialize(format="xml")
            return {
                "status_code": 200,
                "body": body,
                "headers": {"Content-Type": "application/sparql-results+xml"},
            }
        # Default: CSV
        body = results.serialize(format="csv")
        return {
            "status_code": 200,
            "body": body,
            "headers": {"Content-Type": "text/csv"},
        }

    def _exec_construct(
        self, query: str, accept: str
    ) -> Dict[str, Any]:
        result_graph = self.graph.query(query)
        accept_lower = accept.lower()

        if "json" in accept_lower or "json-ld" in accept_lower:
            fmt = "json-ld"
            ct = "application/ld+json"
        elif "turtle" in accept_lower:
            fmt = "turtle"
            ct = "text/turtle"
        elif "n-triples" in accept_lower or "ntriples" in accept_lower:
            fmt = "nt"
            ct = "application/n-triples"
        elif "n-quads" in accept_lower or "nquads" in accept_lower:
            fmt = "nquads"
            ct = "application/n-quads"
        elif "trix" in accept_lower:
            fmt = "trix"
            ct = "application/x-trig"
        elif "trig" in accept_lower:
            fmt = "trig"
            ct = "application/x-trig"
        else:
            fmt = "turtle"
            ct = "text/turtle"

        body = result_graph.serialize(format=fmt)
        return {
            "status_code": 200,
            "body": body,
            "headers": {"Content-Type": ct},
        }

    def _exec_ask(self, query: str, accept: str) -> Dict[str, Any]:
        result = self.graph.query(query)
        body = _serialize_sparql_json(result)
        return {
            "status_code": 200,
            "body": body,
            "headers": {"Content-Type": "application/sparql-results+json"},
        }

    def _exec_describe(
        self, query: str, accept: str
    ) -> Dict[str, Any]:
        return self._exec_construct(query, accept)

    # ------------------------------------------------------------------
    # /update
    # ------------------------------------------------------------------

    def _handle_update(self, body: Optional[str]) -> Dict[str, Any]:
        update = self._extract_update_param(body) if body else None
        if not update:
            return {"status_code": 400, "body": None, "headers": {}}

        upper = update.strip().upper()

        # Special failure cases used by the test suite
        if "failure_upon_deletion" in update:
            if upper.startswith("DROP GRAPH"):
                return {"status_code": 500, "body": None, "headers": {}}
            if "failure_uri_503" in update:
                return {
                    "status_code": 503,
                    "body": None,
                    "headers": {"Retry-After": "5"},
                }

        try:
            self.graph.update(update)
        except Exception as exc:
            return {
                "status_code": 500,
                "body": str(exc),
                "headers": {"Content-Type": "text/plain"},
            }

        return {"status_code": 200, "body": None, "headers": {}}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_query_param(body: str) -> Optional[str]:
        """Extract the ``query`` parameter from form-encoded body."""
        if body.startswith("query="):
            params = __import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl(body)
            for k, v in params:
                if k == "query":
                    return v
            return None
        return body

    @staticmethod
    def _extract_update_param(body: str) -> Optional[str]:
        """Extract the ``update`` parameter from form-encoded body."""
        params = __import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl(body)
        for k, v in params:
            if k == "update":
                return v
        return None

    # ------------------------------------------------------------------
    # Convenience helpers for test setup
    # ------------------------------------------------------------------

    def load_ntriples(self, triples: str, graph_name: Optional[str] = None) -> None:
        """Load N-Triples / N-Quads text into a named graph (or default)."""
        if graph_name:
            g = self.graph.get_context(URIRef(graph_name))
        else:
            g = self.graph
        g.parse(data=triples, format="nquads" if graph_name else "nt")

    def graph_exists(self, graph_name: str) -> bool:
        g = self.graph.get_context(URIRef(graph_name))
        return len(g) > 0
