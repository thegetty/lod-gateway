import sys
import datetime
import json
import hashlib
import os
import math

# Import the utility functions (commandOptions, get, has, put, debug, repeater, etc)
from app.utilities import *

# Import the dependency injector
from app.di import DI

# Import the data model
from app.model import *

# Import the Flask web framework
from flask import Flask, Blueprint, Response, request

# Create a new "activity" route blueprint
activity = Blueprint("activity", __name__)


@activity.route("/activity-stream")
@activity.route("/activity-stream/<path:path>")
@activity.route("/<path:namespace>/activity-stream")
@activity.route("/<path:namespace>/activity-stream/<path:path>")
def activityStream(path=None, namespace=None):
    debug(
        "activityStream(path: %s, namespace: %s) called..." % (path, namespace), level=0
    )

    # Define our default headers to add to the response
    headers = {
        "Server": "MART/1.0",
        "Access-Control-Allow-Origin": "*",
    }

    database = DI.get("database")
    if database:
        connection = database.connect(autocommit=True)
        if connection:
            DI.set("connection", connection)
        else:
            return Response(
                status=500,
                headers={
                    **{"X-Error": "Unable to obtain database connection!",},
                    **headers,
                },
            )
    else:
        return Response(
            status=500,
            headers={**{"X-Error": "Unable to obtain database handler!",}, **headers},
        )

    response = None

    positions = ["first", "last", "current", "prev", "previous", "next", "page"]
    paths = None
    namespace = None
    entity = None
    position = None
    page = None
    UUID = None

    defaultNamespace = os.getenv("LOD_DEFAULT_URL_NAMESPACE", None)
    if isinstance(defaultNamespace, str) and len(defaultNamespace) > 0:
        namespace = defaultNamespace

    # /activity-stream
    # /activity-stream/first
    # /activity-stream/last
    # /activity-stream/page/123
    # /activity-stream/xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    # /museum/collection/activity-stream
    # /museum/collection/activity-stream/first
    # /museum/collection/activity-stream/last
    # /museum/collection/activity-stream/page/123
    # /museum/collection/activity-stream/object/last
    # /museum/collection/activity-stream/object/first
    # /museum/collection/activity-stream/object/page/123
    # /museum/collection/activity-stream/xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

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

    query = {}

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

    start = 1
    count = Activity.recordCount(**query)
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)
    first = 0
    last = 0
    previous = 0
    current = 0
    next = 0
    pages = 0
    data = None

    if limit < 10:
        limit = 10
    elif limit > 1000:
        limit = 1000

    if UUID:
        activity = Activity.findFirst("uuid = :uuid:", bind={"uuid": UUID})
        if activity:
            data = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "partOf": {
                    "id": generateURL(namespace=namespace, entity=entity),
                    "type": "OrderedCollection",
                },
            }

            item = generateActivityStreamItem(
                activity, namespace=namespace, entity=entity
            )
            if isinstance(item, dict):
                data.update(item)

                response = Response(
                    json.dumps(data, indent=4),
                    headers={
                        **{"Content-Type": "application/activity+json;charset=UTF-8",},
                        **headers,
                    },
                    status=200,
                )
            else:
                response = Response(
                    status=404,
                    headers={
                        **{
                            "X-Error": sprintf(
                                "Activity %s was not found!" % (UUID), error=True
                            ),
                        },
                        **headers,
                    },
                )
        else:
            response = Response(
                status=404,
                headers={
                    **{"X-Error": sprintf("Activity %s was not found!" % (UUID)),},
                    **headers,
                },
            )
    elif isinstance(count, int):
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
                        **{"X-Error": "Unsupported Pagination Mnemonic (Current)",},
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
                            headers={
                                **{"X-Error": "Page Offset Out Of Range",},
                                **headers,
                            },
                        )
                elif page == 0:
                    offset = 0
                    current = 0
                    previous = 0
                    next = 0
                else:
                    response = Response(
                        status=400,
                        headers={**{"X-Error": "Invalid Page Offset",}, **headers},
                    )
            elif isinstance(position, str):
                response = Response(
                    status=400,
                    headers={
                        **{
                            "X-Error": sprintf(
                                "Unsupported Pagination Mnemonic (%s)" % (position)
                            ),
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
                    "id": generateURL(namespace=namespace, entity=entity),
                    "startIndex": start,
                    "totalItems": count,
                    "totalPages": pages,
                    "maxPerPage": limit,
                }

                # data["meta"] = {
                # 	"path":      path,
                # 	"uuid":      UUID,
                # 	"namespace": namespace,
                # 	"entity":    entity,
                # 	"position":  position,
                # 	"count":     count,
                # 	"offset":    offset,
                # 	"limit":     limit,
                # 	"previous":  previous,
                # 	"current":   current,
                # 	"next":      next,
                # 	"first":     first,
                # 	"last":      last,
                # 	"page":      page,
                # 	"query":     query,
                # }
                #
                # debug(data, format="JSON")

                activities = Activity.find(**query)
                if activities:
                    debug("Found %d activities..." % (len(activities)), level=1)

                    if len(activities) > 0:
                        if offset == 0:
                            if first:
                                data["first"] = {
                                    "id": generateURL(
                                        namespace=namespace,
                                        entity=entity,
                                        sub=["page", str(first)],
                                    ),
                                    "type": "OrderedCollectionPage",
                                }

                            if last:
                                data["last"] = {
                                    "id": generateURL(
                                        namespace=namespace,
                                        entity=entity,
                                        sub=["page", str(last)],
                                    ),
                                    "type": "OrderedCollectionPage",
                                }
                        else:
                            data["id"] = generateURL(
                                namespace=namespace,
                                entity=entity,
                                sub=["page", str(offset)],
                            )

                            data["partOf"] = {
                                "id": generateURL(namespace=namespace, entity=entity),
                                "type": "OrderedCollection",
                            }

                            if first:
                                data["first"] = {
                                    "id": generateURL(
                                        namespace=namespace,
                                        entity=entity,
                                        sub=["page", str(first)],
                                    ),
                                    "type": "OrderedCollectionPage",
                                }

                            if last:
                                data["last"] = {
                                    "id": generateURL(
                                        namespace=namespace,
                                        entity=entity,
                                        sub=["page", str(last)],
                                    ),
                                    "type": "OrderedCollectionPage",
                                }

                            if previous:
                                data["prev"] = {
                                    "id": generateURL(
                                        namespace=namespace,
                                        entity=entity,
                                        sub=["page", str(previous)],
                                    ),
                                    "type": "OrderedCollectionPage",
                                }

                            if next:
                                data["next"] = {
                                    "id": generateURL(
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
                                    activity, namespace=namespace, entity=entity
                                )
                                if item:
                                    items.append(item)

                            if len(items) > 0:
                                response = Response(
                                    json.dumps(data, indent=4),
                                    headers={
                                        **{
                                            "Content-Type": "application/activity+json;charset=UTF-8",
                                        },
                                        **headers,
                                    },
                                    status=200,
                                )
                            else:
                                response = Response(
                                    status=404,
                                    headers={
                                        **{
                                            "X-Error": "Activity Stream Items Not Found",
                                        },
                                        **headers,
                                    },
                                )
                    else:
                        response = Response(
                            status=404,
                            headers={
                                **{"X-Error": "Activity Stream Items Not Found",},
                                **headers,
                            },
                        )
                else:
                    response = Response(
                        status=404,
                        headers={
                            **{"X-Error": "Activity Stream Items Not Found",},
                            **headers,
                        },
                    )

                if not response:
                    response = Response(
                        json.dumps(data, indent=4),
                        headers={
                            **{
                                "Content-Type": "application/activity+json;charset=UTF-8",
                            },
                            **headers,
                        },
                        status=200,
                    )
        else:
            response = Response(
                status=404,
                headers={**{"X-Error": "No Activity Stream Items Found!",}, **headers},
            )
    else:
        response = Response(
            status=500,
            headers={
                **{"X-Error": "Invalid Activity Stream Record Count!",},
                **headers,
            },
        )

    if not isinstance(response, Response):
        response = Response(
            status=500, headers={**{"X-Error": "Invalid Response Data",}, **headers}
        )

    database.disconnect(connection=connection)

    return response


def generateActivityStreamItem(activity, **kwargs):
    debug(
        "generateActivityStreamItem(activity: %s, kwargs: %s) called..."
        % (activity, kwargs),
        level=1,
    )

    namespace = get(kwargs, "namespace")
    entity = get(kwargs, "entity")

    if isinstance(activity, Activity):
        item = {
            "id": generateURL(namespace=namespace, entity=entity, sub=[activity.uuid]),
            "type": activity.event,
            "actor": None,
            "object": None,
            "created": None,
            "updated": None,
            "published": None,
        }

        created = activity.datetime_created
        if created:
            created = datetime.strptime(created, "%Y-%m-%d %H:%M:%S%z")
            if created:
                created = date("%Y-%m-%dT%H:%M:%S%z", timestamp=created)
                if created:
                    # Fix the timezone offset to add minute separator, as %Z does not work as documented for 3.7+
                    created = created[:-2] + ":" + created[-2:]

        updated = activity.datetime_updated
        if updated:
            updated = datetime.strptime(updated, "%Y-%m-%d %H:%M:%S%z")
            if updated:
                updated = date("%Y-%m-%dT%H:%M:%S%z", timestamp=updated)
                if updated:
                    # Fix the timezone offset to add minute separator, as %Z does not work as documented for 3.7+
                    updated = updated[:-2] + ":" + updated[-2:]

        published = activity.datetime_published
        if published:
            published = datetime.strptime(published, "%Y-%m-%d %H:%M:%S%z")
            if published:
                published = date("%Y-%m-%dT%H:%M:%S%z", timestamp=published)
                if published:
                    # Fix the timezone offset to add minute separator, as %Z does not work as documented for 3.7+
                    published = published[:-2] + ":" + published[-2:]

        if created:
            item["created"] = created

        if updated:
            item["updated"] = updated
        elif created:
            item["updated"] = created

        if published:
            item["published"] = published
        else:
            if updated:
                item["published"] = updated
            elif created:
                item["published"] = created

        record = activity.record
        if isinstance(record, Record):
            _entity = hyphenatedStringFromCamelCasedString(record.entity)

            item["object"] = {
                "id": generateURL(
                    sub=[record.namespace, _entity, record.uuid], base=True
                ),
                "type": record.entity,
            }
        else:
            debug(
                "generateActivityStreamItem() Related Record for %s was invalid!"
                % (activity),
                error=True,
            )

        return item
    else:
        debug("generateActivityStreamItem() Provided Activity was invalid!", error=True)

    return None


def generateURL(**kwargs):
    debug("generateURL(kwargs: %s) called..." % (kwargs), level=1)

    URL = os.getenv("LOD_BASE_URL", None)

    if URL:
        if "namespace" in kwargs:
            if isinstance(kwargs["namespace"], str) and len(kwargs["namespace"]) > 0:
                URL += "/" + kwargs["namespace"]

        if get(kwargs, "base", default=False) == False:
            URL += "/activity-stream"

        if "entity" in kwargs:
            if isinstance(kwargs["entity"], str) and len(kwargs["entity"]) > 0:
                URL += "/" + kwargs["entity"]

        if "sub" in kwargs:
            if isinstance(kwargs["sub"], list) and len(kwargs["sub"]) > 0:
                for sub in kwargs["sub"]:
                    if isinstance(sub, str) and len(sub) > 0:
                        URL += "/" + sub

        return URL

    return None
