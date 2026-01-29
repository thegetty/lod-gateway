from __future__ import annotations  # for python 3.10

import re
import copy

from urllib.parse import urlparse
from typing import Any, Tuple
from pyld import jsonld as pyjsonld

from flaskapp.utilities import join_baseid_and_rel
from flaskapp.errors import ResourceValidationError


validid = re.compile(r"^[A-z0-9-._~:@!$'()*+,;=\/\[\]]+\Z")
LDP_URI = "http://www.w3.org/ns/ldp#"


class Representation:
    "A class to hold the parsed representation of the entity that was POST/PUT/PATCHed to the service."

    def __init__(self, server_root, relative_container, slug=None, json_ld=None):
        # Base really is the critical parameter here - all the 'id's will be made relative to that after all
        # in most/all cases it will be the root container of the LOD Gateway

        # Base should be the root address, including service namespace (eg https://data.getty.edu/research/collection/)
        # relative_container should be the container relative URI (eg 'object/')
        self.base = server_root
        self.relative_container = relative_container
        self.slug = slug
        self._jsonld = None
        self._original = None
        self._id_attr = "@id"
        self._title = None
        self._description = None
        self._toplevelid = None

        if json_ld is not None:
            # Should trigger the property.setter 'json_ld'
            self.json_ld = json_ld

    @classmethod
    def _validate_jsonld(cls, json_ld):
        try:
            # Expand the JSON-LD to check for syntax/structure compliance
            pyjsonld.expand(json_ld)
            return True
        except pyjsonld.JsonLdError:
            return False

    @classmethod
    def _has_top_level_id(cls, json_ld):
        try:
            # return 'id_missing' if no 'id' present
            id_attr = "@id" if "@id" in json_ld.keys() else "id"

            # No top level id (either missing an id value, or )
            if id_attr not in json_ld.keys() or not json_ld[id_attr].strip():
                return False

            if not validid.match(json_ld[id_attr]):
                return False

            # cache the id:
            self._toplevelid = json_ld[id_attr]

            # context @base has to be valid if present too
            if "@context" in json_ld and isinstance(json_ld["@context"], dict):
                if baseurl := json_ld["@context"].get("@base"):
                    # First, if base is present, make sure it is absolute:
                    parsed_baseurl = urlparse(baseurl)
                    if not bool(parsed_baseurl.scheme):
                        raise ValueError("@base value needs to be an absolute URI")

            # all validations succeeded, return OK
            return json_ld[id_attr]
        except ValueError:
            return False

    def has_top_level_id(self):
        return Representation._has_top_level_id(self.json_ld)

    @property
    def is_basic_container(self):
        if not self._jsonld:
            return False

        # default absolute, find prefix if exists
        prefix = LDP_URI
        if "@context" in self._jsonld:
            for k, v in self._jsonld["@context"].items():
                if v == LDP_URI:
                    prefix = f"{k}:"

        # is ldp:BasicContainer part of the top-level 'type' property value, or property list?
        return f"{prefix}BasicContainer" in self._jsonld.get(
            "@type", self._jsonld.get("type", "")
        )

    @property
    def json_ld(self):
        return self._jsonld

    @json_ld.setter
    def json_ld(self, json_ld_input):
        # do a shallow copy so that changes to the top-level dict won't affect the
        # supplied dict.
        json_ld = json_ld_input.copy()

        if Representation._validate_jsonld(json_ld) is False:
            raise ResourceValidationError(
                "The JSONLD supplied is not valid (eg missing top level id/@id)"
            )

        # Now validated, capture the original jsonld with a deep copy, as it can be mutated later
        self._original = copy.deepcopy(json_ld)

        # reset title and description
        self._title = self._description = None

        attr = "id" if "id" in json_ld else "@id"
        self._id_attr = attr
        if context := json_ld.get("@context"):
            if b := context.get("@base"):
                if b == self.base:
                    # Assume it is already in the right form.
                    if self.slug:
                        json_ld = prefix_rdf_ids(
                            json_ld,
                            base_id=self.base,
                            container_path=self.relative_container,
                            slug=self.slug,
                            id_keys=[self._id_attr],
                        )
                    self._jsonld = json_ld
                    return
                elif b.startswith(self.base):
                    # Already partially prefixed
                    # add in the container prefix to make it relative to root
                    container_prefix = b.removeprefix(self.base)
                    if container_prefix.endswith("/"):
                        container_prefix = container_prefix[:-1]

                    json_ld = prefix_rdf_ids(
                        json_ld,
                        base_id=self.base,
                        container_path=container_prefix,
                        slug=self.slug,
                        id_keys=[self._id_attr],
                    )
                    self._jsonld = json_ld
                    return
                else:
                    # Trust that the json_ld doc *is* already relative as @base is present
                    json_ld["@context"]["@base"] = self.base
                    json_ld = prefix_rdf_ids(
                        json_ld,
                        base_id=self.base,
                        container_path=self.relative_container,
                        slug=self.slug,
                        id_keys=[self._id_attr],
                    )
                    self._jsonld = json_ld
                    return

        # in_place changes:
        json_ld = prefix_rdf_ids(
            json_ld,
            base_id=self.base,
            container_path=self.relative_container,
            slug=self.slug,
            id_keys=[self._id_attr],
        )
        json_ld["@context"] = {"@base": self.base}
        self._jsonld = json_ld

    @property
    def slug_id(self):
        return self.slug

    @slug_id.setter
    def slug_id(self, slug_id):
        self.slug = slug_id
        # set the json_ld back to the original request version, and rebase
        self.json_ld = self._original

    @property
    def title(self):
        if self._title is not None:
            return self._title
        else:
            self.get_dcterms()
            return self._title

    @property
    def description(self):
        if self._description is not None:
            return self._description
        else:
            self.get_dcterms()
            return self._description

    def get_dcterms(self):
        self._title = self._description = ""
        expanded = pyjsonld.expand(self.json_ld)

        def _get_value(d):
            return next((x.get("@value") for x in d if "@value" in x), "")

        for graph in expanded:
            for k, v in graph.items():
                match k:
                    case "http://purl.org/dc/terms/title":
                        self._title = _get_value(v)
                    case "http://purl.org/dc/terms/description":
                        self._description = _get_value(v)


def parse_representation(server_root, relative_container, request):
    # check for valid JSON-LD
    # rebase, and return Representation
    # capture the Slug header if present, even though the rebase does not take that into account yet.
    if request.headers["Content-Type"] == "application/ld+json":
        # Slug?
        slug = request.headers.get("Slug") or None
        r = Representation(
            server_root=server_root, relative_container=relative_container, slug=slug
        )
        r.json_ld = request.get_json()
        return r
    else:
        raise ResourceValidationError(
            "Only application/ld+json Content-Type is acceptable"
        )


def prefix_rdf_ids(
    data: dict,
    base_id: str,
    *,
    container_path: str = "",
    id_keys: Tuple[str, ...] = ("id", "@id"),
    inplace: bool = False,
    slug: str = "",
) -> dict:
    """
    Prefix all RDF identifiers in a JSON-LD dict with `base_id`, producing relative IRIs.
    No touching stuff in @context

    Rules
    -----
    1) Only string values under keys in `id_keys` (default: '@id', 'id') are modified.
    2) If an ID already starts with `base_id` (after removing any scheme/host),
       it is not modified again (no repetition).
    3) Any scheme/host (e.g., 'https://example.org') is stripped from both the
       source IDs and the `base_id`.
    4) IDs become *relative IRIs* (no scheme, no host). Fragments are preserved.
    5) Blank node identifiers (e.g., '_:b1') are left unchanged.
    6) '@context' is not traversed or altered.

    eg
    >>> sample = {
    ...   "@graph": [
    ...     {"@id": "https://example.org/items/123"}, # left unchanged
    ...     {"@id": "items/456"},
    ...     {"@id": "#frag"},
    ...     {"@id": "_:b1"},
    ...     {"@id": "/absolute/path"},
    ...     {"@id": "http://another.host/things?id=1#part"}, # left unchanged
    ...   ],
    ...   "@context": {
    ...     "name": "http://schema.org/name"  # left unchanged
    ...   }
    ... }
    >>> out = prefix_rdf_ids(sample, "items/")
    >>> [n["@id"] for n in out["@graph"]]
    ['https://example.org/items/123', 'items/456', 'items#frag', '_:b1', 'items/absolute/path', 'http://another.host/things?id=1#part']
    """

    # slug?
    relative_prefix = container_path.rstrip("/")
    unprefixer = ""
    if slug:
        # create a new top-level id/@id from the container_path and the slug
        # switch to "container_path/slug" for the prefix
        unprefixer = f""
        relative_prefix = join_baseid_and_rel(container_path, slug).rstrip("/")

        altered = False
        for id_attr in id_keys:
            if id_attr in data and not altered:
                # capture the original id value to replace with the new slug-id prefix
                unprefixer = data.get(id_attr, unprefixer)
                data[id_attr] = relative_prefix
                altered = True
        if not altered:
            # add in a top-level id using the first 'id_keys' property
            unprefixer = relative_prefix
            data[id_keys[0]] = relative_prefix

        print(relative_prefix, unprefixer)

    def transform_id(value: str) -> str:
        # Leave blank nodes untouched
        if value.startswith("_:"):
            return value

        # Remove base_id if present
        rel = value.removeprefix(base_id)

        # If the id value is an absolute URI for a different host, leave it be
        parsed_baseurl = urlparse(rel)
        if bool(parsed_baseurl.scheme):
            return rel

        # slug - unprefixer? eg so that "items/1234" with slug 'slug' turns into 'items/slug/1234'
        #        instead of 'items/slug/items/1234' but 'items/999' stays as 'items/999'
        if unprefixer and rel.startswith(unprefixer):
            rel = rel.removeprefix(unprefixer)
            # Join base and the relative part carefully (fragments vs paths)
            return join_baseid_and_rel(relative_prefix, rel).rstrip("/")

        # If already starts with the normalized base, do not repeat the prefix.
        if rel.startswith(container_path):
            return rel

        # Not an id 'owned' by this named graph but still relative, rebase it as expected without a slug.
        return join_baseid_and_rel(container_path, rel)

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            # Do not traverse @context
            items = node.items() if inplace else list(node.items())
            target = node if inplace else {}
            for k, v in items:
                if k == "@context":
                    # Keep as-is
                    if not inplace:
                        target[k] = v
                    continue

                if k in id_keys and isinstance(v, str):
                    new_v = transform_id(v)
                    if inplace:
                        node[k] = new_v
                    else:
                        target[k] = new_v
                else:
                    new_v = walk(v)
                    if inplace:
                        node[k] = new_v
                    else:
                        target[k] = new_v
            return node if inplace else target

        if isinstance(node, list):
            if inplace:
                for i, item in enumerate(node):
                    node[i] = walk(item)
                return node
            else:
                return [walk(item) for item in node]

        # primitives
        return node

    return walk(data)
