"""Pydantic path parameter models for Flask-OpenAPI3.

These models are passed as the `path=` argument to @bp.get() / @bp.post()
decorators so that Flask-OpenAPI3 can generate correct OpenAPI path parameters.

Each model defines a single path parameter matching a Flask URL rule converter
(e.g. ``<path:entity_id>`` -> ``entity_id: str``, ``<int:pagenum>`` -> ``pagenum: int``).
"""

from pydantic import BaseModel, Field, ConfigDict, RootModel

# from uuid import UUID
from typing import Optional

# Example of a query model for GET parameters:
# class EntityFiltersQuery(BaseModel):
#     # Optional parameter with a default fallback value
#     limit: int = Field(
#         default=10,
#         ge=1,
#         le=100,
#         description="Number of results to return per page."
#     )

#     # Optional parameter that defaults to None if not provided
#     status: Optional[str] = Field(
#         default=None,
#         max_length=50,
#         description="Filter entities by their operational status."
#     )

#     # Optional parameter with character length constraints
#     search_term: Optional[str] = Field(
#         default=None,
#         min_length=3,
#         description="Text search query against entity names."
#     )


# Body payloads
class EntityBody(BaseModel):
    # This dictates to flask-openapi3-swagger that 'id' is required
    id: Optional[str] = Field(default=None, description="Standard unique identifier")
    at_id: Optional[str] = Field(
        default=None, alias="@id", description="Alternative semantic identifier"
    )
    type: str = Field(..., description="Entity Type")

    # Correct Pydantic v2 configuration for version 4.x+
    model_config = ConfigDict(extra="allow", populate_by_name=True)


# Body payloads
class PlainBody(BaseModel):
    type: str = Field(..., description="Entity Type")
    model_config = ConfigDict(extra="allow")


JSONL_examples = {
    "Single record ingest": {
        "summary": "Example of how to ingest a single record. Add the whole document, with a newline",
        "value": '{"id": "---relative-identifier---", "type": "....", "etc": {...}, ... }\n',
    },
    "Multiple record ingest": {
        "summary": "Multiple records. Split their JSON-encoded text with newlines",
        "value": '{"id": "qfewf", "... }\n{"id": "qfewf2", "... }\n{"id": "qfewf3", "... }\n',
    },
    "Refresh a record": {
        "summary": "Example of how to reload a single record into the graphstore (requires RDF processing) and LDP container index (if LDP_BACKEND is on)",
        "value": '{"id": "---relative-identifier---", "_refresh": true}\n',
    },
    "Delete record(s)": {
        "summary": "Example of how to delete a record.",
        "value": '{"id": "...", "_delete": "true"}\n',
    },
}


# Shared schema component to avoid writing the example each time
class JSONLSchema(RootModel[str]):
    root: str = Field(
        description="Newline-delimited JSON records. One JSON object per line.",
        examples=JSONL_examples,
    )


# Define multiple content types inside the 'content' object
# eg @api.post('/upload-jsonl', extra_body=JSONLBody)
JSONLBody = {
    "description": "Upload structural records via raw text JSONL stream.",
    "required": True,
    "content": {
        "text/plain": {  # To allow the swagger UI to work properly
            "schema": {
                "type": "string",
            },
            "examples": JSONL_examples,
        },
        "application/x-ndjson": {
            "schema": {
                "type": "string",
            },
            "examples": JSONL_examples,
        },
        "text/jsonl": {
            "schema": {
                "type": "string",
            },
            "examples": JSONL_examples,
        },  # secondary allowed content-type
        "application/json": {
            "schema": {
                "type": "string",
            },
            "examples": JSONL_examples,
        },  # Fallback type
    },
}


def patch_ingest_route(app, ns=None):
    route_path = "/ingest"
    if ns and ns != "/":
        route_path = f"/{ns}/ingest"

    if route_path in app.api_doc["paths"]:
        app.api_doc["paths"][route_path]["post"]["requestBody"] = JSONLBody


# Base Models with validation constraints applied via Field
class EntityIdPath(BaseModel):
    entity_id: str = Field(
        ...,
        description="The relative identifier for a JSON object held in the LOD Gateway.",
    )


class PagenumPath(BaseModel):
    pagenum: int = Field(
        ..., ge=1, description="The page number. Starts at 1 with no upper bound."
    )


class UuidPath(BaseModel):
    # Using Pydantic's native UUID type auto-validates format and updates Swagger UI
    # UUID is a little too narrow for this
    uuid: str = Field(..., description="A valid Universally Unique Identifier (UUID).")


class EntityTypePath(BaseModel):
    entity_type: str = Field(
        ..., max_length=200, description="The type designation string of the entity."
    )


class TargetDatetimePath(BaseModel):
    target_datetime: str = Field(
        ..., description="The target date time (11/10/2025, May 10th 2026, etc)."
    )


class OptionalTargetDatetimeQuery(BaseModel):
    datetime: Optional[str] = Field(
        ...,
        description="The target date time (11/10/2025, May 10th 2026, etc) from a '?datetime=' parameter",
    )


class OptionalSlugQuery(BaseModel):
    slug: Optional[str] = Field(
        default=None,
        description="The slug you intend this item to get when it is uploaded",
    )


# Composite Models combining the validated parameters
class EntityTypePagenumPath(BaseModel):
    entity_type: str = Field(
        ..., max_length=200, description="The type designation string of the entity."
    )
    pagenum: int = Field(
        ..., ge=1, description="The page number. Starts at 1 with no upper bound."
    )


class EntityIdActivityStreamPagenumPath(BaseModel):
    entity_id: str = Field(
        ...,
        description="The relative identifier for a JSON object held in the LOD Gateway.",
    )
    pagenum: int = Field(
        ..., ge=1, description="The page number. Starts at 1 with no upper bound."
    )


# OpenAPI decorator kwargs that should be stripped before passing to Flask's add_url_rule
_OPENAPI_KWARGS = frozenset(
    [
        "tags",
        "summary",
        "responses",
        "description",
        "security",
        "deprecated",
        "external_docs",
        "servers",
        "operation_id",
        "openapi_extensions",
        "path",
    ]
)


def _strip_openapi_kwargs(api):
    """Wrap a blueprint's add_url_rule to strip Flask-OpenAPI3 decorator kwargs.

    Flask-OpenAPI3 passes decorator metadata (tags, summary, responses, etc.) through
    the decorator chain down to Flask's add_url_rule(). Those kwargs are not recognized
    by Flask's Rule class and cause TypeError. This wrapper intercepts the call and
    removes them before delegating to the original method.

    Usage::

        from flask_openapi3 import APIBlueprint
        from flaskapp.openapi_models import _strip_openapi_kwargs

        bp = APIBlueprint("mybp", __name__)
        _strip_openapi_kwargs(bp)

    After calling this, all route decorators on *bp* that use Flask-OpenAPI3 metadata
    will work correctly because the OpenAPI kwargs are stripped before reaching Flask.
    """
    _original = api.add_url_rule

    def _wrapped(*args, **kwargs):
        for key in _OPENAPI_KWARGS:
            kwargs.pop(key, None)
        _original(*args, **kwargs)

    api.add_url_rule = _wrapped
