"""Pydantic response schemas and tag definitions for OpenAPI docs.

Used by route decorators across all blueprints. The OpenAPI spec is
auto-generated from the @app.get() / @app.post() decorators on each
blueprint's route functions.
"""

from pydantic import BaseModel
from flask_openapi3 import Tag

# ---------------------------------------------------------------------------
# Tags (groupings for Swagger UI sidebar)
# ---------------------------------------------------------------------------

health_tag = Tag(name="health", description="Health-check endpoints")
records_tag = Tag(name="records", description="Record CRUD operations")
ingest_tag = Tag(name="ingest", description="Batch ingest endpoint")
activity_tag = Tag(name="activity", description="Activity Stream endpoints")
sparql_tag = Tag(name="sparql", description="SPARQL query endpoint")
timegate_tag = Tag(name="timegate", description="Memento versioning endpoints")
home_tag = Tag(name="home", description="Home page and dashboard")
ldp_tag = Tag(name="ldp", description="Linked Data Platform endpoints")

TAGS = [
    health_tag,
    records_tag,
    ingest_tag,
    activity_tag,
    sparql_tag,
    timegate_tag,
    home_tag,
    ldp_tag,
]

# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class HealthOK(BaseModel):
    """Successful health-check response (plain text "OK")."""

    pass


class ErrorDetail(BaseModel):
    """Single error item in an errors array."""

    status: int
    title: str
    detail: str


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""

    errors: list[ErrorDetail]
