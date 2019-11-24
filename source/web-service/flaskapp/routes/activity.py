import sys
from datetime import datetime
import json
import hashlib
import os
import math

from flask import Flask, Blueprint, Response, request

from app.utilities import (
    debug,
    date,
    camelCasedStringFromHyphenatedString,
    hyphenatedStringFromCamelCasedString,
    isNumeric,
    isUUIDv4,
    sprintf,
)
from app.di import DI
from app.model import Activity
from flaskapp.routes.utilities import (
    errorResponse,
    DEFAULT_HEADERS,
    instantiateDatabase,
)


# Create a new "activity" route blueprint
activity = Blueprint("activity", __name__)


@activity.route("/activity-stream")
@activity.route("/activity-stream/<path:path>")
@activity.route("/<path:namespace>/activity-stream")
@activity.route("/<path:namespace>/activity-stream/<path:path>")
def activityStream(path=None, namespace=None):

    namespace = os.getenv("LOD_DEFAULT_URL_NAMESPACE", None)
    headers = DEFAULT_HEADERS
    limit = _getLimit(request)
    offset = request.args.get("offset", default=0, type=int)
    paths, position, page, UUID, entity = _parsePath(path)

    database, connection, error_response = instantiateDatabase()
    if error_response:
        return error_response

    query = _buildQuery(namespace, entity)
    count = Activity.recordCount(**query)

    if not count:
        response = Response(
            status=500,
            headers={**{"X-Error": "Invalid Activity Stream Record Count!"}, **headers},
        )
    elif UUID:
        response = _generateSingleItem(UUID, namespace, entity, headers)
    else:
        response = _generatePage(
            count, limit, position, headers, offset, query, namespace, entity, page
        )

    database.disconnect(connection=connection)
    return response


def generateActivityStreamItem(activity, namespace=None, entity=None, record=None):

    if activity == None:
        return None

    item = {
        "id": _generateURL(namespace=namespace, entity=entity, sub=[activity.uuid]),
        "type": activity.event,
        "created": _formatDate(activity.datetime_created),
        "actor": None,
        "updated": _formatDate(activity.datetime_updated),
        "published": _formatDate(activity.datetime_published),
        "object": _generateActivityStreamObject(record),
    }

    if item["updated"] == None:
        item["updated"] = item["created"]

    if item["published"] == None:
        item["published"] = item["updated"]

    return item


def _generateURL(namespace=None, entity=None, sub=[], base=False):
    """Create a URL string from relevant fragments
    
    Args:
        namespace (String, optional): A namespace for the URL
        entity (String, optional): The ID of the entity
        sub (list, optional): A list of additional URL parts
        base (bool, optional): Should the "activity-stream" part be added?
    
    Returns:
        String: The generated URL string
    """
    base_url = os.getenv("LOD_BASE_URL", "")

    if base:
        as_prefix = None
    else:
        as_prefix = "activity-stream"

    parts = [base_url, namespace, as_prefix, entity, "/".join(sub)]
    parts = [item for item in parts if item]
    return "/".join(parts)


def _formatDate(date_string):
    """Convert a timestampz into a XML DateTime Object
    
    Args:
        date_string (string): The timestamp representation
    
    Returns:
        String: the XML DateTime Representation, or None if passed None

    Raises:
        ValueError on failure to parse a passed date
    """
    if date_string == None:
        return None

    try:
        val = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S%z")
        val = date("%Y-%m-%dT%H:%M:%S%z", timestamp=val)
        # Fix the timezone offset to add minute separator, as %Z does not work as documented for 3.7+
        val = val[:-2] + ":" + val[-2:]
        return val
    except:
        raise ValueError()


def _generateActivityStreamObject(record):
    """Generate the AS representation of a Record
    
    Args:
        record (Record): The object or generate
    
    Returns:
        Dict: The AS representation of the object, or None if the record is invalid
    """
    try:
        record_type = hyphenatedStringFromCamelCasedString(record.entity)
        return {
            "id": _generateURL(
                sub=[record.namespace, record_type, record.uuid], base=True
            ),
            "type": record.entity,
        }
    except Exception as e:
        return None


def _parsePath(path):
    paths = []
    position = None
    page = None
    UUID = None
    entity = None
    positions = ["first", "last", "current", "prev", "previous", "next", "page"]

    if isinstance(path, str) and len(path) > 0:
        paths = path.split("/")
        if len(paths) >= 1:
            if paths[0] in positions:
                position = paths[0]

                if position == "page":
                    if len(paths) >= 2 and isNumeric(paths[1]):
                        page = int(paths[1])
            else:
                if isUUIDv4(paths[0]):
                    UUID = paths[0]
                else:
                    entity = paths[0]

                    if len(paths) >= 2:
                        if paths[1] in positions:
                            position = paths[1]

                            if position == "page":
                                if len(paths) >= 3 and isNumeric(paths[2]):
                                    page = int(paths[2])

    return paths, position, page, UUID, entity


def _buildQuery(namespace, entity):
    if namespace:
        if entity:
            _entity = camelCasedStringFromHyphenatedString(entity)

            query = {
                "clause": "namespace = :namespace: AND entity = :entity:",
                "bind": {"namespace": namespace, "entity": _entity},
            }
        else:
            query = {
                "clause": "namespace = :namespace:",
                "bind": {"namespace": namespace},
            }
    else:
        query = {}
    return query


def _getLimit(request):
    limit = request.args.get("limit", default=100, type=int)
    if limit < 10:
        limit = 10
    elif limit > 1000:
        limit = 1000
    return limit


def _generateSingleItem(UUID, namespace, entity, headers):
    activity = Activity.findFirst("uuid = :uuid:", bind={"uuid": UUID})
    if activity:
        data = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "partOf": {
                "id": _generateURL(namespace=namespace, entity=entity),
                "type": "OrderedCollection",
            },
        }

        item = generateActivityStreamItem(
            activity, namespace=namespace, entity=entity, record=activity.record
        )
        if isinstance(item, dict):
            data.update(item)

            return Response(
                json.dumps(data, indent=4),
                headers={
                    **{"Content-Type": "application/activity+json;charset=UTF-8"},
                    **headers,
                },
                status=200,
            )
        else:
            return Response(
                status=404,
                headers={
                    **{
                        "X-Error": sprintf(
                            "Activity %s was not found!" % (UUID), error=True
                        )
                    },
                    **headers,
                },
            )
    else:
        return Response(
            status=404,
            headers={
                **{"X-Error": sprintf("Activity %s was not found!" % (UUID))},
                **headers,
            },
        )


def _generatePage(
    count, limit, position, headers, offset, query, namespace, entity, page
):
    response = None
    previous = 0
    first = 0
    last = 0
    next = 0
    current = 0
    pages = 0
    data = None
    start = 1

    if count > 0:
        pages = math.ceil(count / limit)
        first = 1
        last = pages

        if position == "first":
            previous = first - 1
            offset = first
            next = first + 1
        elif position == "last":
            previous = last - 1
            offset = last
            next = last + 1
        elif position == "current":
            response = Response(
                status=400,
                headers={
                    **{"X-Error": "Unsupported Pagination Mnemonic (Current)"},
                    **headers,
                },
            )
        elif position == "page":
            if page:
                if page >= 1 and page <= last:
                    offset = page
                    current = page
                    previous = offset - 1
                    next = offset + 1
                else:
                    response = Response(
                        status=400,
                        headers={**{"X-Error": "Page Offset Out Of Range"}, **headers},
                    )
            elif page == 0:
                offset = 0
                current = 0
                previous = 0
                next = 0
            else:
                response = Response(
                    status=400,
                    headers={**{"X-Error": "Invalid Page Offset"}, **headers},
                )
        elif isinstance(position, str):
            response = Response(
                status=400,
                headers={
                    **{
                        "X-Error": sprintf(
                            "Unsupported Pagination Mnemonic (%s)" % (position)
                        )
                    },
                    **headers,
                },
            )

        if not response:
            if previous < first:
                previous = 0

            if next > last:
                next = 0

            if offset > 0:
                _offset = offset - 1
            elif offset == 0:
                _offset = offset
            else:
                _offset = 0

            query["limit"] = limit
            query["offset"] = limit * _offset
            query["ordering"] = {"id": "ASC"}

            data = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "summary": "The Getty MART Repository's Recent Activity",
                "type": "OrderedCollection",
                "id": _generateURL(namespace=namespace, entity=entity),
                "startIndex": start,
                "totalItems": count,
                "totalPages": pages,
                "maxPerPage": limit,
            }

            activities = Activity.find(**query)
            if activities:
                debug("Found %d activities..." % (len(activities)), level=1)

                if len(activities) > 0:
                    if offset == 0:
                        if first:
                            data["first"] = {
                                "id": _generateURL(
                                    namespace=namespace,
                                    entity=entity,
                                    sub=["page", str(first)],
                                ),
                                "type": "OrderedCollectionPage",
                            }

                        if last:
                            data["last"] = {
                                "id": _generateURL(
                                    namespace=namespace,
                                    entity=entity,
                                    sub=["page", str(last)],
                                ),
                                "type": "OrderedCollectionPage",
                            }
                    else:
                        data["id"] = _generateURL(
                            namespace=namespace,
                            entity=entity,
                            sub=["page", str(offset)],
                        )

                        data["partOf"] = {
                            "id": _generateURL(namespace=namespace, entity=entity),
                            "type": "OrderedCollection",
                        }

                        if first:
                            data["first"] = {
                                "id": _generateURL(
                                    namespace=namespace,
                                    entity=entity,
                                    sub=["page", str(first)],
                                ),
                                "type": "OrderedCollectionPage",
                            }

                        if last:
                            data["last"] = {
                                "id": _generateURL(
                                    namespace=namespace,
                                    entity=entity,
                                    sub=["page", str(last)],
                                ),
                                "type": "OrderedCollectionPage",
                            }

                        if previous:
                            data["prev"] = {
                                "id": _generateURL(
                                    namespace=namespace,
                                    entity=entity,
                                    sub=["page", str(previous)],
                                ),
                                "type": "OrderedCollectionPage",
                            }

                        if next:
                            data["next"] = {
                                "id": _generateURL(
                                    namespace=namespace,
                                    entity=entity,
                                    sub=["page", str(next)],
                                ),
                                "type": "OrderedCollectionPage",
                            }

                        items = data["orderedItems"] = []

                        for index, activity in enumerate(activities):
                            debug(
                                "%06d/%06d ~ %s ~ id = %s"
                                % (index, count, activity, activity.id),
                                indent=1,
                                level=2,
                            )

                            item = generateActivityStreamItem(
                                activity,
                                namespace=namespace,
                                entity=entity,
                                record=activity.record,
                            )
                            if item:
                                items.append(item)

                        if len(items) > 0:
                            response = Response(
                                json.dumps(data, indent=4),
                                headers={
                                    **{
                                        "Content-Type": "application/activity+json;charset=UTF-8"
                                    },
                                    **headers,
                                },
                                status=200,
                            )
                        else:
                            response = Response(
                                status=404,
                                headers={
                                    **{"X-Error": "Activity Stream Items Not Found"},
                                    **headers,
                                },
                            )
                else:
                    response = Response(
                        status=404,
                        headers={
                            **{"X-Error": "Activity Stream Items Not Found"},
                            **headers,
                        },
                    )
            else:
                response = Response(
                    status=404,
                    headers={
                        **{"X-Error": "Activity Stream Items Not Found"},
                        **headers,
                    },
                )

            if not response:
                response = Response(
                    json.dumps(data, indent=4),
                    headers={
                        **{"Content-Type": "application/activity+json;charset=UTF-8"},
                        **headers,
                    },
                    status=200,
                )
    else:
        response = Response(
            status=404,
            headers={**{"X-Error": "No Activity Stream Items Found!"}, **headers},
        )
    return response
