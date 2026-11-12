"""Shared support for the Activity Stream GET routes.

Single implementation of the stream URL builders, the item / collection /
page docs, and the validator-carrying response helper for the ETags, used by
the three stream providers: the global stream (``routes/activity.py``), the
type-filtered stream (``routes/activity_entity.py``), and the per-record
streams (``routes/records.py``).

Streams are served with the AS 2.0-registered media type
``application/activity+json`` and carry a strong content-hash ``ETag`` and a
``Last-Modified`` header with full 304 revalidation support (RFC 9110).
Events carry ``endTime`` with a ``Z`` designator; the legacy ``created`` term
is included by default and omitted while the start-time flag
``ACTSTR_INCLUDE_CREATED`` is ``False``
"""

import hashlib

from datetime import timezone

from flask import Response, current_app, request
from werkzeug.http import http_date

from flaskapp.utilities import format_datetime, format_utc_datetime

AS_CONTEXT = "https://www.w3.org/ns/activitystreams"
ACTIVITY_JSON = "application/activity+json"

# TODO Optimize: work out a good way to cache the runtime-level config terms
# that are often looked up here. I don't like it, but it is better to get this
# refactor in place first, and then work on optimizing speed. It should result
# in a quite small but noticeable speed up once the values are cached.

# URL constructors


def generate_url(sub=[], base=False):
    """Create a URL string from relevant fragments (global family).

    Filtered join: empty parts (an unset namespace) are dropped, so the
    result is single-slash even in a no-namespace deployment.

    Args:
        sub (list, optional): A list of additional URL parts
        base (bool, optional): Should the "activity-stream" part be added?

    Returns:
        String: The generated URL string
    """
    base_url = current_app.config["idPrefix"]

    if base:
        as_prefix = None
    else:
        as_prefix = "activity-stream"

    parts = [item for item in [base_url, as_prefix, "/".join(sub)] if item]
    return "/".join(parts)


def url_base(entity_id=None):
    """Create the (namespace) base URL.

    Raw concatenation, no filtering: a no-namespace deployment carries a
    trailing slash. That is the current home-page and type/per-record
    behavior and is preserved as-is, not normalized.

    Args:
        entity_id (str, optional): Append /<entity_id> when given

    Returns:
        String: The base URL (plus optional entity id)
    """

    base_url = current_app.config["idPrefix"]

    if entity_id:
        return "/".join([base_url, entity_id])
    else:
        return base_url


# There were a lot of URLs, so maybe a little overkill to do all these as
# separate, but it helps keep them in line, and should make it easy to change.
def stream_url():
    """Global family: the top-level stream root URL."""
    return generate_url()


def stream_page_url(page):
    """Global family: the URL of page ``page`` of the stream."""
    return generate_url(sub=["page", str(page)])


def stream_item_url(item_id):
    """Global family: the URL of a single event."""
    return generate_url(sub=[str(item_id)])


def object_url(entity_id):
    """Global family: the URL of an object (no activity-stream prefix)."""
    return generate_url(base=True, sub=[str(entity_id)])


def type_stream_url(entity_type):
    """Type family: the stream root URL for an entity type."""
    return url_base() + "/activity-stream/type/" + entity_type.lower()


def type_page_url(page, entity_type):
    """Type family: the URL of page ``page`` of a type stream."""
    return type_stream_url(entity_type) + "/page/" + str(page)


def type_item_url(item_id):
    """Type family: the URL of a single event."""
    return url_base() + "/activity-stream/" + str(item_id)


def type_object_url(entity_id):
    """Type family: the URL of an object."""
    return url_base() + "/" + entity_id


def record_stream_url(entity_id, page=None):
    """Record family: the stream root URL for an entity (plus page)."""
    url = url_base() + "/" + entity_id + "/activity-stream"
    if page:
        url = url + "/page/" + str(page)
    return url


def record_item_url(item_id):
    """Record family: the URL of a single event."""
    return url_base() + "/activity-stream/" + item_id


def record_object_url(entity_id):
    """Record family: the URL of an object."""
    return url_base(entity_id)


# Document builders


def build_event_item(
    family, item_id, event, datetime_created, entity_id, entity_type, standalone=False
):
    """Build one Activity Stream event item.

    Args:
        family (str): "global" | "type" | "record" - selects that family's
            URL helpers for ``id`` and ``object.id`` (the families' ID forms
            diverge in no-namespace deployments, so they are never collapsed)
        item_id: The event uuid
        event: The event name (item ``type``)
        datetime_created: The event's creation datetime (naive-UTC or aware)
        entity_id: The referenced object's entity id
        entity_type: The referenced object's type
        standalone (bool): True for a single-item document, which gains a
            top-level ``@context`` so it is JSON-LD-valid on its own; page
            item lists pass the default False (the page-level context applies)

    Returns:
        dict: The event item. ``created`` (legacy rendering, existing
        ``format_datetime``) is included by default and omitted while
        ``ACTSTR_INCLUDE_CREATED`` is ``False``; ``endTime`` is always
        present with a ``Z`` designator.
    """
    match family:
        case "global":
            id_, object_id = stream_item_url(item_id), object_url(entity_id)
        case "type":
            id_, object_id = type_item_url(item_id), type_object_url(entity_id)
        case "record":
            id_, object_id = record_item_url(item_id), record_object_url(entity_id)
        case _:
            raise ValueError(f"Unknown activity stream family: {family!r}")

    item = {"id": id_, "type": event}
    if current_app.config.get("ACTSTR_INCLUDE_CREATED", True):
        item["created"] = format_datetime(datetime_created)
    item["endTime"] = format_utc_datetime(datetime_created)
    item["object"] = {"id": object_id, "type": entity_type}
    if standalone:
        item["@context"] = AS_CONTEXT

    return item


def build_collection(collection_id, count, total_pages, page_url_fn, summary=None):
    """Build an OrderedCollection document.

    Args:
        collection_id: The collection ``id``
        count: The total event count (``totalItems``)
        total_pages: Caller-computed page count - the correct formula depends
            on the provider's pagination strategy (pk-window vs OFFSET/LIMIT),
            so it is never derived from ``count`` here
        page_url_fn: Callable mapping a page number to its URL
        summary (str, optional): The collection ``summary`` (defaults to the
            ``AS_DESC`` config)

    Returns:
        dict: The collection; ``first``/``last`` are omitted when ``count`` is 0
    """
    if summary is None:
        summary = current_app.config["AS_DESC"]

    data = {
        "@context": AS_CONTEXT,
        "summary": summary,
        "type": "OrderedCollection",
        "id": collection_id,
        "totalItems": count,
    }

    if count:
        data["first"] = {"id": page_url_fn(1), "type": "OrderedCollectionPage"}
        data["last"] = {
            "id": page_url_fn(total_pages),
            "type": "OrderedCollectionPage",
        }

    return data


def build_page(pagenum, total_pages, page_id, part_of_id, page_url_fn, items):
    """Build an OrderedCollectionPage document.

    Args:
        pagenum (int): The current page number
        total_pages (int): The total page count
        page_id: This page's ``id``
        part_of_id: The parent collection's ``id``
        page_url_fn: Callable mapping a page number to its URL
        items (list): The built event items (0..ITEMS_PER_PAGE entries)

    Returns:
        dict: The page; ``next``/``prev`` are present when applicable
    """
    data = {
        "@context": AS_CONTEXT,
        "type": "OrderedCollectionPage",
        "id": page_id,
        "partOf": {"id": part_of_id, "type": "OrderedCollection"},
    }

    if pagenum < total_pages:
        data["next"] = {"id": page_url_fn(pagenum + 1), "type": "OrderedCollectionPage"}

    if pagenum > 1:
        data["prev"] = {"id": page_url_fn(pagenum - 1), "type": "OrderedCollectionPage"}

    data["orderedItems"] = items

    return data


# Response maker (which adds in the extras needed)
# last_modified/Etag/Content-type + response


def as_response(data, last_modified=None):
    """Serialize a document and return a response with its validators.

    Args:
        data (dict): The document (collection, page, or item)
        last_modified (datetime, optional): The max ``datetime_created`` of
            the events the document covers (page: its items; collection: all
            its events; item: its own). Naive is treated as UTC. When ``None``
            (an empty document) the ``Last-Modified`` header is omitted.

    Returns:
        Response: 200 with ``application/activity+json`` content type, a
        strong content-hash ``ETag``, and ``Last-Modified``; or 304 (empty
        body, no content type) when the request's ``If-None-Match`` or
        ``If-Modified-Since`` validators match.

    """
    # Using the current_app.json.dumps() + .compact is the trick to
    # pick up the provider's ensure_ascii / sort_keys / default.
    if (current_app.json.compact is None and current_app.debug) or (
        current_app.json.compact is False
    ):
        layout = {"indent": 2}
    else:
        layout = {"separators": (",", ":")}
    body = (current_app.json.dumps(data, **layout) + "\n").encode("utf-8")

    # Normalize to aware UTC and floor to whole seconds
    lm = None
    if last_modified is not None:
        if last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=timezone.utc)
        else:
            last_modified = last_modified.astimezone(timezone.utc)
        lm = last_modified.replace(microsecond=0)

    etag = hashlib.sha256(body).hexdigest()

    # 304 logic (RFC 9110 precedence: If-None-Match first).
    # The spec is actually quite specific in the ordering, hence the following:
    # If-None-Match > If-Modified-Since mostly, but with caveats.

    # TODO look at the resource ETag handling and see if that needs to be
    # updated to match. It's used by the clients currently, so I don't want to
    # break that for this feature update.

    # TODO #2 If the page has a 'next', it can be considered as immutable by
    # downstream caches. Maybe there is merit in adding a header like:
    # Cache-Control: public, max-age=31536000, immutable
    # Counter to that, if the cache keeps latest requested pages, a full pull
    # might affect that so that human-requested pages drop out of the cache.
    # Bots can wait.
    matched_tag = None
    if request.if_none_match.star_tag:
        # * matches any representation
        matched_tag = "*"
    else:
        for tag in request.if_none_match:
            # Flask-Compress rewrites the ETag of every compressed 2xx to
            # "<hash>:<algo>"
            # Stripping a single suffix so such clients can 304. gzip + ETag is
            # more awkward than I had thought.
            normalized = tag
            if ":" in normalized:
                normalized = normalized.split(":", 1)[0]
            if normalized == etag:
                matched_tag = tag
                break

    if matched_tag is None and "If-None-Match" not in request.headers:
        # RFC 9110 §13.2.2: a recipient MUST ignore If-Modified-Since when
        # If-None-Match is present (a stale INM must 200, not 304, even if
        # the IMS header is current).
        ims = request.if_modified_since
        if ims is not None and lm is not None and lm <= ims:
            matched_tag = etag

    if matched_tag is not None:
        response = Response(b"", status=304)
        response.headers["ETag"] = f'"{matched_tag}"' if matched_tag != "*" else "*"
        if lm is not None:
            response.headers["Last-Modified"] = http_date(lm)
        # A 304 carries no body, hence no content type.
        if "Content-Type" in response.headers:
            del response.headers["Content-Type"]
        return response

    response = Response(body, status=200, content_type=ACTIVITY_JSON)
    response.headers["ETag"] = f'"{etag}"'
    if lm is not None:
        response.headers["Last-Modified"] = http_date(lm)
    return response
