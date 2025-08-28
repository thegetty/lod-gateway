import re

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

from pyld import jsonld
from pyld.jsonld import JsonLdError

from flaskapp.conneg import reformat_to_jsonld

from flaskapp.base_graph_utils import base_graph_filter, get_url_prefixes_from_context
from flaskapp.graph_prefix_bindings import get_bound_graph

validid = re.compile(r"^[A-z0-9-._~:@!$'()*+,;=\/\[\]]+\Z")


class Representation:
    "A class to hold the parsed representation of the entity that was POST/PUT/PATCHed to the service."

    def __init__(self, base):
        # Base really is the critical parameter here - all the 'id's will be made relative to that after all
        # in most/all cases it will be the root container of the LOD Gateway
        self.base = base
        self._json_ld = None
        self._original = None
        self._original_format = None

    @classmethod
    def _validate_jsonld(cls, json_ld):
        try:
            # return 'id_missing' if no 'id' present
            id_attr = "@id" if "@id" in json_ld.keys() else "id"

            # No top level id (either missing an id value, or )
            if id_attr not in json_ld.keys() or not json_ld[id_attr].strip():
                return False

            if not validid.match(json_ld[id_attr]):
                return False

            # all validations succeeded, return OK
            return True
        except ValueError:
            return False

    @property
    def json_ld(self):
        return self._jsonld

    @json_ld.setter
    def json_ld(self, json_ld):
        if Representation._validate_jsonld(json_ld) is False:
            raise ResourceValidationError(
                "The JSONLD supplied is not valid (eg missing top level id/@id)"
            )
        attr = "id" if "id" in json_ld else "@id"
        if context := json_ld.get("@context"):
            if "@base" in context:
                b = context["@base"]
                if json_ld[attr].split(":")[0] in ALLOWED_SCHEMES:
                    # json_ld has a @base BUT the IDs start with a URI scheme!
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

                    attr = "id" if "id" in json_ld else "@id"
                    json_ld = containerRecursiveCallback(
                        data=json_ld,
                        attr=attr,
                        callback=idPrefixer,
                        prefix=container_prefix,
                        recursive=True,
                    )
                # Trust that the json_ld doc *is* already relative as @base is present
                json_ld["@context"]["@base"] = self.base
                self._jsonld = json_ld
        else:
            attr = "id" if "id" in json_ld else "@id"
            # just in case, remove the base prefix if it exists
            json_ld = containerRecursiveCallback(
                data=json_ld,
                attr=attr,
                callback=idUnPrefixer,
                prefix=self.base,
                recursive=True,
            )
            # json_ld document has no context... hmm odd.

            json_ld["@context"] = {"@base": self.base}
            self._jsonld = json_ld


def parse_representation(self, request):
    pass
