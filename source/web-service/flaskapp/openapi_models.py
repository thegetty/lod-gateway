"""Pydantic path parameter models for Flask-OpenAPI3.

These models are passed as the `path=` argument to @bp.get() / @bp.post()
decorators so that Flask-OpenAPI3 can generate correct OpenAPI path parameters.

Each model defines a single path parameter matching a Flask URL rule converter
(e.g. ``<path:entity_id>`` -> ``entity_id: str``, ``<int:pagenum>`` -> ``pagenum: int``).
"""

from pydantic import BaseModel


class EntityIdPath(BaseModel):
    entity_id: str


class IdPath(BaseModel):
    id: str


class PagenumPath(BaseModel):
    pagenum: int


class PagenumStrPath(BaseModel):
    pagenum: str


class UuidPath(BaseModel):
    uuid: str


class EntityTypePath(BaseModel):
    entity_type: str


class TargetDatetimePath(BaseModel):
    target_datetime: str


class EntityTypePagenumPath(BaseModel):
    entity_type: str
    pagenum: str


class EntityIdActivityStreamPagenumPath(BaseModel):
    entity_id: str
    pagenum: str


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
