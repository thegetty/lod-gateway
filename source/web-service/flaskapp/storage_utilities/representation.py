import requests
import json
import time

from flask import current_app

from flaskapp.utilities import (
    containerRecursiveCallback,
    idPrefixer,
    idUnPrefixer,
    ALLOWED_SCHEMES,
    quads_to_triples,
    graph_filter,
)

from flaskapp.errors import ResourceValidationError

import traceback

from pyld import jsonld
from pyld.jsonld import JsonLdError

from flaskapp.base_graph_utils import base_graph_filter, get_url_prefixes_from_context
from flaskapp.graph_prefix_bindings import get_bound_graph


class Representation:
    "A class to hold the parsed representation of the entity that was POST/PUT/PATCHed to the service."

    def __init__(self, base):
        # Base really is the critical parameter here - all the 'id's will be made relative to that after all
        # in most/all cases it will be the root container of the LOD Gateway
        self.base = None
        self._jsonld = None
        self._original = None
        self._original_format = None

    @classmethod
    def _validate_jsonld(cls, jsonld):
        try:
            # return 'id_missing' if no 'id' present
            id_attr = "@id" if "@id" in jsonld.keys() else "id"

            # No top level id (either missing an id value, or )
            if id_attr not in jsonld.keys() or not data[id_attr].strip():
                return False

            # all validations succeeded, return OK
            return True
        except ValueError as e:
            return False

    @property
    def jsonld(self):
        return self._jsonld

    @jsonld.setter
    def jsonld(self, jsonld):
        attr = "id" if "id" in jsonld else "@id"
        if context := jsonld.get("@context"):
            if "@base" in context:
                b = context["@base"]
                if jsonld[attr].split(":") in ALLOWED_SCHEMES:
                    # jsonld has a @base BUT the IDs start with a URI scheme!
                    # failure!
                    raise ResourceValidationError(
                        "JSONLD document has a @base in its context, but the top-level '@id' is a FQDN of some kind."
                    )
                if self.base.startswith(b):
                    # Already partially prefixed
                    # add in the container prefix to make it relative to root
                    container_prefix = b.removeprefix(self.base)
                    if container_prefix.endswith("/"):
                        container_prefix = container_prefix[:-1]

                    attr = "id" if "id" in jsonld else "@id"
                    jsonld = containerRecursiveCallback(
                        data=jsonld,
                        attr=attr,
                        callback=idPrefixer,
                        prefix=container_prefix,
                        recursive=True,
                    )
                # Trust that the jsonld doc *is* already relative as @base is present
                jsonld["@context"]["@base"] = self.base
                self._jsonld = jsonld
        else:
            attr = "id" if "id" in jsonld else "@id"
            # just in case, remove the base prefix if it exists
            jsonld = containerRecursiveCallback(
                data=jsonld,
                attr=attr,
                callback=idUnPrefixer,
                prefix=self.base,
                recursive=True,
            )
            # jsonld document has no context... hmm odd.
            jsonld["@context"]["@base"] = self.base
            self._jsonld = jsonld


def parse_representation(self, request):
    pass
