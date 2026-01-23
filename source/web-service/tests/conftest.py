from __future__ import annotations

import json
import pytest
import os
import re
import requests
import urllib.parse

from datetime import datetime, timezone
from uuid import uuid4

from flaskapp import create_app
from flaskapp.utilities import Event

from flaskapp.models import db
from flaskapp.models.activity import Activity
from flaskapp.models.record import Record

from flaskapp.storage_utilities.container import get_container
from flaskapp.storage_utilities.record import (
    record_create,
    process_activity,
)


from dataclasses import dataclass
from typing import Optional, Dict, Any
import uuid


@pytest.fixture
def app(mocker):
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def app_ldpapi(mocker):
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    flask_app.config["LDP_BACKEND"] = True
    flask_app.config["LDP_API"] = True
    flask_app.config["LDP_AUTOCREATE_CONTAINERS"] = True
    yield flask_app


@pytest.fixture
def app_no_rdf(mocker):
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    flask_app.config["PROCESS_RDF"] = False
    flask_app.config["LDP_BACKEND"] = False
    flask_app.config["LDP_API"] = False
    flask_app.config["SPARQL_QUERY_ENDPOINT"] = None
    flask_app.config["SPARQL_UPDATE_ENDPOINT"] = None

    yield flask_app


@pytest.fixture
def current_app(app):
    with app.app_context():
        yield app


@pytest.fixture
def current_app_no_rdf(app_no_rdf):
    with app_no_rdf.app_context():
        yield app_no_rdf


@pytest.fixture
def client_ldpapi(app_ldpapi):
    testing_client = app_ldpapi.test_client()
    ctx = app_ldpapi.app_context()
    ctx.push()
    yield testing_client  # this is where the testing happens!
    ctx.pop()


@pytest.fixture
def ldp_fixture_app(app_ldpapi, test_db, ldp_sample_containers):
    # Add some basic objects. One for the basic containers, and all the annotations into /annotations/ml-test/
    # for pagination testing.
    options = AnnotationOptions()

    options.creator = {"name": "Some random person"}
    options.motivation = "assessing"
    options.language = "en"
    for m in FAKE_MOVIE_ANNOTATIONS:
        doc = create_web_annotation(
            target=m["target"],
            target_generator="https://www.imdb.com/",
            body_string=m["body_string"],
            annotation_id_base="annotations/ml-test/",
            options=options,
        )
        record_create(doc, process_activity=True)
    test_db.session.commit()

    yield current_app


@pytest.fixture
def auth_token(current_app):
    yield current_app.config["AUTH_TOKEN"]


@pytest.fixture
def namespace(current_app):
    yield current_app.config["NAMESPACE"]


@pytest.fixture
def base_url(current_app, namespace):
    b_url = current_app.config["BASE_URL"]
    return f"{b_url}/{namespace}"


@pytest.fixture
def client(app):
    testing_client = app.test_client()

    ctx = app.app_context()
    ctx.push()
    yield testing_client  # this is where the testing happens!
    ctx.pop()


@pytest.fixture
def client_no_rdf(app_no_rdf):

    testing_client = app_no_rdf.test_client()

    ctx = app_no_rdf.app_context()
    ctx.push()
    yield testing_client  # this is where the testing happens!
    ctx.pop()


@pytest.fixture
def test_db(current_app):
    # `SQLALCHEMY_DATABASE_URI` maps to the `DATABASE` environment variable through Flask's create_app() setup
    if ".amazonaws.com" in current_app.config["SQLALCHEMY_DATABASE_URI"]:
        pytest.exit(
            ">>> WARNING – Cannot run the PyTest suite as the `DATABASE` environment variable currently references an AWS-hosted database, which will be *DESTROYED* by running the test suite! <<<"
        )
    db.drop_all()
    db.create_all()
    # get or create-and-get the root container to ensure it always is in the test db
    _ = get_container("/")
    return db


@pytest.fixture
def test_db_no_rdf(current_app_no_rdf):
    # `SQLALCHEMY_DATABASE_URI` maps to the `DATABASE` environment variable through Flask's create_app() setup
    if ".amazonaws.com" in current_app_no_rdf.config["SQLALCHEMY_DATABASE_URI"]:
        pytest.exit(
            ">>> WARNING – Cannot run the PyTest suite as the `DATABASE` environment variable currently references an AWS-hosted database, which will be *DESTROYED* by running the test suite! <<<"
        )
    db.drop_all()
    db.create_all()
    # get or create-and-get the root container to ensure it always is in the test db
    _ = get_container("/")
    return db


@pytest.fixture
def sample_record(test_db):
    def _sample_record():
        record = Record(
            entity_id=str(uuid4()),
            entity_type="Object",
            datetime_created=datetime(2019, 11, 22, 13, 2, 53),
            datetime_updated=datetime(2019, 12, 18, 11, 22, 7),
            data={"example": "data"},
        )
        test_db.session.add(record)
        test_db.session.commit()
        return record

    return _sample_record


@pytest.fixture
def sample_activity(test_db, sample_record):
    def _sample_activity(record_id):

        if not db.session.get(Record, record_id):
            record = sample_record()
            record_id = record.id

        activity = Activity(
            uuid=str(uuid4()),
            datetime_created=datetime(2019, 11, 22, 13, 2, 53),
            record_id=record_id,
            event=Event.Create.name,
        )
        test_db.session.add(activity)
        test_db.session.commit()
        return activity

    return _sample_activity


@pytest.fixture
def sample_data(sample_record, sample_activity):
    record = sample_record()
    activity = sample_activity(record.id)
    return {"record": record, "activity": activity}


@pytest.fixture
def sample_record_with_ids(test_db):
    def _sample_record():
        record = Record(
            entity_id=str(uuid4()),
            entity_type="Object",
            datetime_created=datetime(2019, 11, 22, 13, 2, 53),
            datetime_updated=datetime(2019, 12, 18, 11, 22, 7),
            data={
                "id": "object/123",
                "example": "data",
                "nested": [
                    {
                        "id": "object/456",
                    },
                    {
                        "id": "object/789",
                    },
                ],
            },
        )
        test_db.session.add(record)
        test_db.session.commit()
        return record

    return _sample_record


@pytest.fixture
def sample_idprefixdata(sample_rdfrecord_with_context):
    return sample_rdfrecord_with_context()


@pytest.fixture
def sample_rdfrecord_with_context(test_db):
    def _sample_record():
        record = Record(
            entity_id=str(uuid4()),
            entity_type="Object",
            datetime_created=datetime(2020, 11, 22, 13, 2, 53),
            datetime_updated=datetime(2020, 12, 18, 11, 22, 7),
            data={
                "@context": {
                    "dc": "http://purl.org/dc/elements/1.1/",
                    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                    "_label": {"@id": "http://www.w3.org/2000/01/rdf-schema#label"},
                    "_prefixedlabel": {"@id": "rdfs:label"},
                },
                "@id": "rdfsample1",
                "rdfs:seeAlso": [
                    {
                        "_label": "This is a meaningless bit of data to test if the idprefixer leaves the id alone",
                        "@id": "dc:description",
                    },
                ],
            },
        )
        test_db.session.add(record)
        test_db.session.commit()
        return record

    return _sample_record


@pytest.fixture
def linguisticobject():
    def _generator(name, id):
        return {
            "@context": "https://linked.art/ns/v1/linked-art.json",
            "id": id,
            "type": "LinguisticObject",
            "rdfs:label": name,
            "content": name,
            "classified_as": [
                {
                    "id": "https://data.getty.edu/local/thesaurus/aspace-subject-topical",
                    "type": "Type",
                    "_label": "Subject Heading - Topical",
                }
            ],
        }

    return _generator


@pytest.fixture
def sample_jsonldrecord_with_id(test_db, linguisticobject):
    def _sample_record(name, id):
        record = Record(
            entity_id=id,
            entity_type="LinguisticObject",
            datetime_created=datetime(2019, 11, 22, 13, 2, 53),
            datetime_updated=datetime(2019, 12, 18, 11, 22, 7),
            data=linguisticobject(name, id),
        )
        test_db.session.add(record)
        test_db.session.commit()
        return record

    return _sample_record


@pytest.fixture
def sample_activity_with_ids(test_db, sample_record_with_ids):
    def _sample_activity(record_id):

        if not db.session.get(Record, record_id):
            record = sample_record_with_ids()
            record_id = record.id

        activity = Activity(
            uuid=str(uuid4()),
            datetime_created=datetime(2019, 11, 22, 13, 2, 53),
            record_id=record_id,
            event=Event.Create.name,
        )
        test_db.session.add(activity)
        test_db.session.commit()
        return activity

    return _sample_activity


@pytest.fixture
def sample_data_with_ids(sample_record_with_ids, sample_activity_with_ids):
    record = sample_record_with_ids()
    activity = sample_activity_with_ids(record.id)
    return {"record": record, "activity": activity}


@pytest.fixture
def ldp_sample_containers(test_db, namespace):
    parent = get_container("/")

    for title, desc, ident in [
        ("Basic Object Container /object/", "Auto-generated container", "/object/"),
        (
            "Basic Object Container /document/",
            "Auto-generated container",
            "/documents/",
        ),
        (
            "Basic Object Container /component/",
            "Auto-generated container",
            "/components/",
        ),
        (
            "Basic Object Container /annotations/",
            "Auto-generated container",
            "/annotations/",
        ),
    ]:
        parent.new_child_container(
            ident,
            dctitle=title,
            dcdescription=desc,
            db_dialect=current_app.config["DB_DIALECT"],
        )

    test_db.session.commit()

    # Setup /annotations/ml-test/ as an example
    anno = get_container("/annotations/")
    anno.new_child_container(
        "/annotations/ml-test/",
        dctitle="ML test annotation Container",
        dcdescription="Annotation collections in this container are for test purposes and not ready for public consumption",
        db_dialect=current_app.config["DB_DIALECT"],
    )
    test_db.session.commit()


@pytest.fixture(autouse=True)
def requests_mocker(requests_mock):
    """The `requests_mocker()` method supports mocking requests to the graph store, which is inaccessible
    from within CircleCI. The `requests_mocker()` method provides support for mocking successful
    HTTP requests to the graph store, and providing appropriate responses for the limited set of queries
    performed by the /ingest endpoint's `process_graphstore_record_set()` method, as well as support
    for generating failed requests to mimic networking issues or connection time-outs.
    """

    def mocker_text_callback(request, context):
        print(f"MOCKED REQUEST, begin handling -: {request.url}")

        if request.path_url.endswith("/status"):
            context.status_code = 200
            return json.dumps(
                {
                    "status": "healthy",
                }
            )
        elif request.path_url.endswith("/sparql") or request.path_url.endswith(
            "/update"
        ):  # TODO: this is not portable
            sparql = None
            print("MOCKED REQUEST -: Treating as SPARQL query")
            if request.body.startswith("query=") or request.body.startswith("update="):
                params = urllib.parse.parse_qsl(request.body)
                if params:
                    for param in params:
                        if param[0] == "query" or param[0] == "update":
                            sparql = param[1]
                            break

            if sparql:
                print(f"MOCKED REQUEST -: SPARQL detected: {sparql}")
                if sparql.startswith("SELECT"):
                    context.status_code = 200
                    return json.dumps(
                        {
                            "results": {
                                "bindings": [
                                    {
                                        "count": {
                                            "value": 0,
                                        }
                                    }
                                ],
                            },
                        }
                    )
                elif sparql.startswith("INSERT DATA"):
                    context.status_code = 200
                    return None
                elif sparql.startswith("DELETE {GRAPH <"):
                    if "failure_uri_503" in sparql:
                        context.status_code = 503
                        context.headers["Retry-After"] = 5
                    else:
                        # Graph replace SPARQL update
                        context.status_code = 200
                    return None
                elif sparql.startswith("DROP SILENT GRAPH"):
                    context.status_code = 200
                    return None
                elif sparql.startswith("DROP GRAPH"):
                    if "failure_upon_deletion" in sparql:
                        context.status_code = 500
                    else:
                        context.status_code = 200
                    return None
                elif (
                    sparql.startswith(
                        "PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>"
                    )
                    and "document/2" in sparql
                ):
                    print("HIT MOCKED document 2 response")
                    context.status_code = 200
                    context.headers = {"Content-Type": "text/turtle"}
                    # real world response from fuseki
                    return b'@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .\n@prefix crm:   <http://www.cidoc-crm.org/cidoc-crm/> .\n@prefix dc:    <http://purl.org/dc/elements/1.1/> .\n\n<http://localhost:5100/document/2>\n        dc:description  "test document 2" ;\n        dc:title        "test document 2" ;\n        dc:type         "Subject Heading - Topical" ;\n        dc:type         <https://data.getty.edu/local/thesaurus/aspace-subject-topical> .\n'.decode(
                        "utf-8"
                    )

        else:
            print(f"*** unhandled mock request: {request.path_url}")

        context.status_code = 400
        return None

    query_endpoint = os.getenv("SPARQL_QUERY_ENDPOINT")
    update_endpoint = os.getenv("SPARQL_UPDATE_ENDPOINT")

    # Configure the default mock handlers; these rely on the `mocker_text_callback()` method defined above
    query_pattern = re.compile(query_endpoint.replace("/sparql", "/(.*)"))
    update_pattern = re.compile(
        update_endpoint.replace("/update", "/(.*)")
    )  # TODO: this is not portable

    for pattern in (query_pattern, update_pattern):
        requests_mock.options(pattern, text=mocker_text_callback)
        requests_mock.head(pattern, text=mocker_text_callback)
        requests_mock.get(pattern, text=mocker_text_callback)
        requests_mock.post(pattern, text=mocker_text_callback)

    # Configure the good mock handlers; these rely on the `mocker_text_callback()` method defined above
    query_pattern = re.compile(
        query_endpoint.replace("http://", "mock-pass://").replace("/sparql", "/(.*)")
    )
    update_pattern = re.compile(
        update_endpoint.replace("http://", "mock-pass://").replace(
            "/update", "/(.*)"
        )  # TODO: this is not portable
    )

    for pattern in (query_pattern, update_pattern):
        requests_mock.options(pattern, text=mocker_text_callback)
        requests_mock.head(pattern, text=mocker_text_callback)
        requests_mock.get(pattern, text=mocker_text_callback)
        requests_mock.post(pattern, text=mocker_text_callback)

    # Configure the fail mock handlers; these rely on the mocker to throw the configured exception
    query_pattern = re.compile(
        query_endpoint.replace("http://", "mock-fail://").replace("/sparql", "/(.*)")
    )
    update_pattern = re.compile(
        update_endpoint.replace("http://", "mock-fail://").replace(
            "/update", "/(.*)"
        )  # TODO: this is not portable
    )

    for pattern in (query_pattern, update_pattern):
        requests_mock.options(pattern, exc=requests.exceptions.ConnectionError)
        requests_mock.head(pattern, exc=requests.exceptions.ConnectionError)
        requests_mock.get(pattern, exc=requests.exceptions.ConnectionError)
        requests_mock.post(pattern, exc=requests.exceptions.ConnectionError)

    # Allow all other non-matched URL patterns to be routed to real HTTP requests
    pattern = re.compile("http(s)://(.*)")
    requests_mock.options(pattern, real_http=True)
    requests_mock.head(pattern, real_http=True)
    requests_mock.get(pattern, real_http=True)
    requests_mock.post(pattern, real_http=True)
    requests_mock.put(pattern, real_http=True)
    requests_mock.patch(pattern, real_http=True)
    requests_mock.delete(pattern, real_http=True)

    yield requests_mock


@pytest.fixture
def create_annotation_fn():
    return create_web_annotation


@pytest.fixture
def annotation_options():
    a = AnnotationOptions()
    return a


@dataclass(frozen=True)
class AnnotationOptions:
    """
    Optional parameters to enrich the annotation.
    - annotation_id: Provide a stable ID; otherwise a URN UUID is generated.
    - created: ISO 8601 timestamp; otherwise UTC 'now' is used.
    - motivation: A Web Annotation motivation, e.g., "commenting", "tagging", "linking".
    - creator: A dict identifying the agent (e.g., {"id": "...", "type": "Person", "name": "..."})
    - language: RFC 5646 language tag for textual body, e.g., "en", "en-GB" (only used with body_string).
    - format_: MIME type of textual body, defaults to "text/plain" (only used with body_string).
    """

    annotation_id: Optional[str] = None
    created: Optional[str] = None
    motivation: Optional[str] = None
    creator: Optional[Dict[str, Any]] = None
    language: Optional[str] = None
    format_: Optional[str] = None


def create_web_annotation(
    *,
    target: str,
    body_string: Optional[str] = None,
    body_uri: Optional[str] = None,
    body_generator: Optional[str] = None,
    target_generator: Optional[str] = None,
    annotation_id_base: Optional[str] = "",
    options: Optional[AnnotationOptions] = None,
) -> Dict[str, Any]:
    """
    Parameters:
        target: str
            The IRI of the target resource (becomes {"id": target}).
        body_string: Optional[str]
            The literal textual content for the annotation body.
        body_uri: Optional[str]
            The IRI of the body resource; used as {"id": body_uri}.
        body_generator/target_generator: Optional[str]
            If present, will add the verbatim value as a 'generator' property value to the respective object.
            body_generator has no effect if it is a body_string.
        options: Optional[AnnotationOptions]
            Optional enrichment parameters (id, created, motivation, creator, language, format_).

    Returns:
        dict: A JSON-LD-compliant Web Annotation object.

    Raises:
        ValueError: If neither or both of `body_string` and `body_uri` are provided,
                    or if `target` is missing/empty.
    """
    if not isinstance(target, str) or not target.strip():
        raise ValueError("`target` must be a non-empty string (IRI).")

    has_string = body_string is not None and body_string != ""
    has_uri = body_uri is not None and body_uri != ""
    if has_string == has_uri:  # either both True or both False
        raise ValueError(
            "Provide exactly one of `body_string` or `body_uri` (but not both)."
        )

    opts = options or AnnotationOptions()

    anno_id = opts.annotation_id or f"{annotation_id_base}{uuid.uuid4()}"
    created_iso = opts.created or datetime.now(timezone.utc).isoformat()

    annotation: Dict[str, Any] = {
        "@context": "https://www.w3.org/ns/anno.jsonld",
        "id": anno_id,
        "type": "Annotation",
        "created": created_iso,
        "target": {"id": target},
    }

    if target_generator:
        annotation["target"]["generator"] = target_generator

    # motivation is optional per the model
    if opts.motivation:
        annotation["motivation"] = opts.motivation

    # creator is optional; should itself be a JSON-LD Agent-like structure but tbh
    # we tend to just use {'name': '....'}.
    if opts.creator:
        annotation["creator"] = opts.creator

    # Build body
    if has_string:
        body_obj: Dict[str, Any] = {
            "type": "TextualBody",
            "value": body_string,
            "format": opts.format_ or "text/plain",
        }
        if opts.language:
            body_obj["language"] = opts.language
        annotation["body"] = body_obj
    else:
        # body as an IRI reference
        annotation["body"] = {"id": body_uri}
        if body_generator:
            annotation["body"]["generator"] = body_generator

    return annotation


FAKE_MOVIE_ANNOTATIONS = (
    [
        {
            "target": "https://www.imdb.com/title/tt0000001/",
            "body_string": "Critics highlight confident direction, memorable performances, and resonant themes; minor pacing quibbles appear, yet consensus finds the film compelling and emotionally rewarding.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000002/",
            "body_string": "Audiences praise stunning cinematography and layered storytelling; a few note uneven tone, but overall sentiment applauds ambition, craft, and lasting impact.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000003/",
            "body_string": "Reviewers celebrate tight writing, textured characters, and assured pacing; occasional predictability is mentioned without dampening strong enthusiasm.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000004/",
            "body_string": "Widely admired for atmosphere and mood, with standout acting and a haunting score; some find the ending abrupt, though most consider it striking and memorable.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000005/",
            "body_string": "Praised for bold vision and emotional depth, blending intimate drama with spectacle; minor critiques target exposition, yet reception remains highly positive.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000006/",
            "body_string": "Critics commend elegant structure and compelling arcs; dialogue shines, while a few lament familiarity; overall, reviews favor craftsmanship and heart.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000007/",
            "body_string": "Viewers applaud relentless momentum, sharp editing, and charismatic leads; detractors cite thin subplots, but general consensus deems it exhilarating.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000008/",
            "body_string": "Acclaimed for nuanced performances and careful world-building; some pacing lulls surface, yet reviews regard it as immersive and thoughtful.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000009/",
            "body_string": "Celebrated for inventive staging, thematic richness, and confident tone; occasional tonal whiplash is forgiven amid overall admiration.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000010/",
            "body_string": "Reviewers note graceful character work, lyrical visuals, and affecting score; a handful call it slow, though many cherish its quiet power.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000011/",
            "body_string": "Praise centers on fearless performances and taut direction; some critique convenience in plotting; consensus appreciates intensity and emotional clarity.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000012/",
            "body_string": "Critics laud precise storytelling, witty dialogue, and thematic weight; minor complaints about length arise, but reception stays enthusiastic.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000013/",
            "body_string": "Audiences admire craftsmanship, textured sound design, and striking images; a few question plausibility, yet sentiment remains strongly favorable.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000014/",
            "body_string": "Applauded for confident storytelling and emotional resonance; some uneven pacing is noted, but most consider it gripping and heartfelt.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000015/",
            "body_string": "Widely praised for atmosphere, meticulous details, and committed acting; minor narrative detours divide critics, though admiration dominates.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000016/",
            "body_string": "Reviews highlight elegant visuals, sustained tension, and moral complexity; a few find character motivations opaque, yet acclaim is strong.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000017/",
            "body_string": "Critics celebrate brisk pacing, sly humor, and polished set pieces; some call it derivative, but overall reaction is delighted.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000018/",
            "body_string": "Warmly received for compassion, thematic depth, and standout lead; sporadic melodrama comments appear, though consensus appreciates its sincerity.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000019/",
            "body_string": "Viewers praise intricate plotting, visual flair, and emotional stakes; a few mention convoluted twists, yet reviews remain largely positive.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000020/",
            "body_string": "Noted for immersive world-building, measured performances, and assured tone; minor repetitiveness is overlooked amid broad approval.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000021/",
            "body_string": "Critics admire the film’s wit, confident rhythm, and resonant themes; some wish for deeper supporting arcs; overall reception is enthusiastic.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000022/",
            "body_string": "Lauded for inventive structure and evocative imagery; a divisive finale sparks discussion, yet praise outweighs reservations.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000023/",
            "body_string": "Reviewers emphasize emotional honesty, grounded performances, and subtle humor; a handful consider it slight, but many find it touching.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000024/",
            "body_string": "Commended for kinetic energy, memorable antagonist, and confident direction; some criticize thin characterization, though excitement prevails.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000025/",
            "body_string": "Audiences appreciate meticulous craft, layered subtext, and bold choices; occasional confusion surfaces, yet admiration is strong.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000026/",
            "body_string": "Praised for balance of spectacle and intimacy, with a magnetic lead; a few pacing dips are noted, but overall impressions are glowing.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000027/",
            "body_string": "Critics hail rich atmosphere, striking color, and confident symbolism; detractors cite opacity, while many celebrate its artistry.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000028/",
            "body_string": "Reviewers admire taut suspense, economical storytelling, and satisfying payoff; some desire deeper backstories, yet consensus is favorable.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000029/",
            "body_string": "Applauded for thought-provoking themes, memorable score, and elegant pacing; minor quibbles target predictability, but acclaim dominates.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000030/",
            "body_string": "Warm reception for charming script, heartfelt moments, and lively ensemble; a few jokes miss, yet the film delights.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000031/",
            "body_string": "Celebrated for audacious vision, commanding performances, and resonant allegory; some uneven tone is forgiven amid admiration.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000032/",
            "body_string": "Viewers cite tight editing, compelling stakes, and confident world-building; minor exposition clunkiness appears, but energy wins over.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000033/",
            "body_string": "Critics commend intricate character dynamics and lyrical craftsmanship; a handful find it slow, yet many call it mesmerizing.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000034/",
            "body_string": "Praised for blend of humor and pathos, anchored by humane performances; some formula elements appear, though warmth prevails.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000035/",
            "body_string": "Admired for meticulous production design, tactile soundscape, and confident suspense; a few label it chilly, but reviews are positive.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000036/",
            "body_string": "Reviewers applaud narrative economy, striking images, and a compelling arc; occasional clichés are outweighed by craft.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000037/",
            "body_string": "Strong notices for heartfelt storytelling, credible relationships, and grounded direction; minor sentimentality is noted, yet affection is widespread.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000038/",
            "body_string": "Critics praise muscular pacing, inventive set pieces, and charismatic chemistry; thin villains are mentioned, but thrills satisfy.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000039/",
            "body_string": "Admired for intelligence and restraint, with an unforgettable climax; a few call it austere, yet esteem is high.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000040/",
            "body_string": "Warm acclaim for textured ensemble, nuanced script, and evocative music; some find the structure meandering, though impact lingers.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000041/",
            "body_string": "Viewers celebrate emotional heft, deft humor, and quietly dazzling visuals; minor third-act wobble aside, reception is glowing.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000042/",
            "body_string": "Critics enjoy brisk plotting, clever reversals, and satisfying catharsis; a few nitpick coincidences, yet praise dominates.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000043/",
            "body_string": "Lauded for atmospheric tension, confident minimalism, and an empathetic core; some wish for more answers, but admiration persists.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000044/",
            "body_string": "Reviews applaud humane tone, generous humor, and heartfelt performances; slight pacing issues are overshadowed by charm.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000045/",
            "body_string": "Acclaimed for thematic ambition, elegant framing, and commanding lead work; occasional opacity divides viewers, yet esteem is strong.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000046/",
            "body_string": "Audiences admire propulsive action, clear geography, and practical effects; character depth is modest, but excitement never flags.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000047/",
            "body_string": "Critics note poetic imagery, subtle performances, and affecting intimacy; a deliberately slow tempo rewards patient viewers.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000048/",
            "body_string": "Praise centers on confident tone, sharp humor, and generous spirit; a few gags overstay, though goodwill remains high.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000049/",
            "body_string": "Reviewers celebrate craftsmanship, emotional stakes, and a resonant finale; small logic gaps are easily forgiven.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000050/",
            "body_string": "Widely admired for bold choices, muscular direction, and layered subtext; some unevenness aside, impact is considerable.",
        },
    ]
    + [
        {
            "target": f"https://www.imdb.com/title/tt{str(5000000 + i).zfill(7)}/",
            "body_string": (
                "Reviewers praise confident direction, engaging performances, and strong craft; "
                "occasional pacing concerns arise, but overall sentiment remains positive and appreciative."
            ),
        }
        for i in range(51, 201)
    ]
    + [
        {
            "target": f"https://www.imdb.com/title/tt{str(6000000 + i).zfill(7)}/",
            "body_string": (
                "Critics highlight striking visuals, thematic depth, and assured storytelling; "
                "some note familiar beats, yet consensus considers it compelling and rewarding."
            ),
        }
        for i in range(201, 251)
    ]
    + [
        {
            "target": f"https://www.imdb.com/title/tt{str(7000000 + i).zfill(7)}/",
            "body_string": (
                "Audiences commend immersive atmosphere, resonant score, and memorable moments; "
                "minor quibbles exist, but reviews trend warmly overall."
            ),
        }
        for i in range(251, 301)
    ]
)
