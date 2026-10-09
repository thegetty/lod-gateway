# Activity Streams

The LOD Gateway generates an Activity Streams 2.0-compliant change history for every record stored in the system. Each create, update, or delete operation produces an Activity Stream entry. These entries are accessible through paginated collection endpoints, per-record streams, entity-type filtered streams, and datetime-based navigation.

([back to README](/README.md))

## Overview

Activity Stream endpoints return JSON-encoded [Activity Streams 2.0](https://www.w3.org/TR/activitystreams-core/) data structures. The root endpoint returns an `OrderedCollection` with `totalItems` and pagination links. Paginated endpoints return `OrderedCollectionPage` objects with `orderedItems`, `next`, and `prev` links.

Each activity item follows the structure:

```json
{
  "id": "{base-url}/{namespace}/activity-stream/{uuid}",
  "type": "Create",
  "created": "2025-01-15T10:30:00+00:00",
  "endTime": "2025-01-15T10:30:00+00:00",
  "object": {
    "id": "{base-url}/{namespace}/{entity-id}",
    "type": "HumanMadeObject"
  }
}
```

The `type` field reflects the operation performed: `Create`, `Update`, or `Delete`. The `object` field contains the resource identifier and entity type at the time of the activity.

## Endpoints

### GET /activity-stream

Returns the root Activity Stream as an `OrderedCollection`. No authentication required.

**Response:**

```json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "summary": "Getty Activity Stream (Example)",
  "type": "OrderedCollection",
  "id": "http://localhost:5100/museum/collection/activity-stream",
  "totalItems": 1542,
  "first": {
    "id": "http://localhost:5100/museum/collection/activity-stream/page/1",
    "type": "OrderedCollectionPage"
  },
  "last": {
    "id": "http://localhost:5100/museum/collection/activity-stream/page/16",
    "type": "OrderedCollectionPage"
  }
}
```

The `summary` value is set via the `LOD_AS_DESC` environment variable.

### GET /activity-stream/page/{pagenum}

Returns a single page of activity items as an `OrderedCollectionPage`. No authentication required.

The number of items per page is controlled by the `ITEMS_PER_PAGE` environment variable (default: 100).

**Response:**

```json
{
  "@context": "https://www.w3.org/ns/activitystreams",
  "type": "OrderedCollectionPage",
  "id": "http://localhost:5100/museum/collection/activity-stream/page/1",
  "partOf": {
    "id": "http://localhost:5100/museum/collection/activity-stream",
    "type": "OrderedCollection"
  },
  "next": {
    "id": "http://localhost:5100/museum/collection/activity-stream/page/2",
    "type": "OrderedCollectionPage"
  },
  "orderedItems": [
    {
      "id": "http://localhost:5100/museum/collection/activity-stream/a1b2c3d4",
      "type": "Create",
      "created": "2025-01-15T10:30:00+00:00",
      "endTime": "2025-01-15T10:30:00+00:00",
      "object": {
        "id": "http://localhost:5100/museum/collection/object/1234",
        "type": "HumanMadeObject"
      }
    }
  ]
}
```

**Status codes:**

- `200` -- page found and returned
- `404` -- page number is out of bounds (less than 1 or greater than total pages)

### GET /activity-stream/{uuid}

Returns a single activity item by its UUID. No authentication required.

**Example:**

```bash
curl http://localhost:5100/museum/collection/activity-stream/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Status codes:**

- `200` -- activity item found
- `404` -- no activity item with that UUID exists

### GET /activity-stream/type/{entity-type}

Returns an `OrderedCollection` filtered to a specific entity type. Entity types are case-insensitive. No authentication required.

**Example:**

```bash
curl http://localhost:5100/museum/collection/activity-stream/type/person
```

Returns the root collection for activities involving records of type `Person`, with `totalItems`, `first`, and `last` pagination links.

**Status codes:**

- `200` -- entity type exists, collection returned
- `404` -- no records of that entity type exist in the system

### GET /activity-stream/type/{entity-type}/page/{pagenum}

Returns a paginated `OrderedCollectionPage` for a specific entity type. No authentication required.

**Example:**

```bash
curl http://localhost:5100/museum/collection/activity-stream/type/person/page/2
```

**Status codes:**

- `200` -- page found and returned
- `404` -- page number out of bounds or entity type does not exist

### GET /activity-stream/skip-to-datetime/{target-datetime}

Redirects to the activity stream page containing the closest activity item to a given datetime. This endpoint accepts a broad range of datetime formats, parsed via the `dateparser` library. No authentication required.

The endpoint finds the earliest activity created at or after the given datetime and calculates which page contains it. It issues an HTTP `302` redirect to that page.

**Example:**

```bash
curl -I http://localhost:5100/museum/collection/activity-stream/skip-to-datetime/2025-01-15T10:00:00
```

Returns:

```
HTTP/1.1 302 FOUND
Location: http://localhost:5100/museum/collection/activity-stream/page/5
```

This endpoint also accepts the datetime as a query parameter:

```bash
curl -I "http://localhost:5100/museum/collection/activity-stream/skip-to-datetime?datetime=2025-01-15"
```

**Status codes:**

- `200` (redirect `302`) -- datetime parsed, page redirect issued
- `400` -- datetime was not specified or could not be parsed
- `404` -- no activities found at or after the given datetime

### GET {entity-id}/activity-stream

Returns the Activity Stream for a single record. This endpoint is available on any resource and returns paginated activity items for that specific entity. No authentication required.

**Example:**

```bash
curl http://localhost:5100/museum/collection/object/1234/activity-stream
```

Returns an `OrderedCollection` scoped to that entity, with pagination links.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ITEMS_PER_PAGE` | `100` | Number of activity items per page |
| `LOD_AS_DESC` | `LOD Gateway` | Description text used in Activity Stream `summary` field and dashboard |

## Response Headers

Activity Stream endpoints return standard JSON responses with `Content-Type: application/json`. The Gateway includes the `X-LODGATEWAY-CAPABILITIES` header on all responses.

## Use Cases

- **Audit trails** -- track all changes to records for compliance and debugging
- **Change notification** -- poll the stream for new activity since a known datetime
- **Data migration** -- use entity-type filtering to isolate changes for specific record types
- **Debugging** -- inspect the create/update/delete history of a specific record via the per-record stream