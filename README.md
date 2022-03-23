# LOD Gateway

This repository contains the code used to convert various Getty systems of record into their [Linked.art](http://www.linked.art) representations.

## Components

The LOD Gateway contains one production container: `web-service`; for development purposes, a containerized `postgres` service and a containerized graph store, `fuseki`, are also included.

## Setup Instructions

_(This assumes that you have [Docker](https://www.docker.com/products/docker-desktop) installed.)_

    git clone https://github.com/thegetty/lod-gateway
    cd lod-gateway
    cp .env.example .env
    docker-compose build
    docker-compose up

To shut the application down:

    docker-compose down

When first creating an application instance, the application database schema must be manually created through the Alembic database migration tool for SQLAlchemy. With the proper database connection defined in the `.env` file, exec into a locally running `web-service` container and execute:

    flask db upgrade

or, from the host command line:

    docker exec `docker ps -q -f publish=5100` flask db upgrade

## Testing the Application

_Run the python unit tests_

While the application is running,

```bash
docker-compose run --rm \
    -e APPLICATION_NAMESPACE="ns" \
    -e DATABASE=sqlite:// \
    -e AUTHORIZATION_TOKEN=AuthToken \
    web pytest
```

will run the tests, and

```bash
docker-compose run --rm \
    -e APPLICATION_NAMESPACE="ns" \
    -e DATABASE=sqlite:// \
    -e AUTHORIZATION_TOKEN=AuthToken \
    web ptw
```

will run `pywatch`, which will watch for file changes and re-run the tests automatically.

## Deployment Options

Configuration is managed through environment variables. In development, these are set through the `.env` file, and in Staging and Production evironments, these values can be managed in a secrets management system like Vault. In testing environments, the `.env.example` file is used directly.

```
LOD_AS_DESC                 # Textual description of the deployed LOD Gateway

AUTHORIZATION_TOKEN=        # Token required for 'Ingest' functionality, i.e. loading
                            # records into the LOD Gateway. The value should 
                            # be formatted as "Bearer {AUTHORIZATION_TOKEN}" in
                            # the HTTP POST request Authorization header.

DATABASE=                   # This should be the full URL to the database
                            # for example, postgresql://mart:mart@postgres/mart.
                            # If APPLICATION_NAMESPACE=local/thesaurus, then a local sqlite db
                            # is used. The entry should be DATABASE=sqlite:////app/app.db

BASE_URL=                   # This should be the base URL of the application and 
                            # for RDF URIs. For example, https://data.getty.edu

APPLICATION_NAMESPACE=      # This should be the 'vanity' portion of the URL
                            # for example, "museum/collection"

RDF_NAMESPACE=              # This variable is optional and should only be set if the
                            # namespace in the RDF data should differ from the value set
                            # in APPLICATION_NAMESPACE and there is a specific need
                            # to prefix the relative URLs in the JSON-LD documents
                            # differently for triples in the graph store, such as for testing
                            # or for specially staged loads. In such cases, these development
                            # or special staging instances of the LOD Gateway must
                            # share the same base URL as their corresponding production
                            # or staging instance, that is, they should be hosted under
                            # the same domain name. If no RDF_NAMESPACE variable is provided,
                            # the LOD Gateway defaults to APPLICATION_NAMESPACE for data loaded
                            # into the graph store.

PROCESS_RDF=                # The value must be "True" to enable processing of JSON-LD into 
                            # RDF triples on ingest. If enabled, two other environment variables
                            # must be set to the SPARQL endpoints (query and update):
                            # SPARQL_QUERY_ENDPOINT and SPARQL_UPDATE_ENDPOINT. When PROCESS_RDF is
                            # set to "False", the LOD Gateway acts as a simple document store with no RDF
                            # component.

FLASK_GZIP_COMPRESSION =    # The value must be "True" to enable gzip compression option

PREFIX_RECORD_IDS=          # Configure the Prefixing of Record "id" Values:
                            # The default behaviour is for all "id" values in a record to
                            # be discovered recursively and to be prefixed if necessary,
                            # if they are not already a HTTP(S) URL ("http(s)://...").
                            # The default behaviour will take place if `PREFIX_RECORD_IDS`
                            # is absent from the application's environment, or if defined
                            # and configured explicitly as `PREFIX_RECORD_IDS=RECURSIVE`.
                            # The other available prefixing behaviours are to prefix only
                            # the top-level "id" of the record, which may be achieved by
                            # setting `PREFIX_RECORD_IDS=TOP`, or to disable all prefixing
                            # of record "id" values by setting `PREFIX_RECORD_IDS=NONE`.

KEEP_LAST_VERSION=          # Set this to True to enable the retention of previous
                            # versions of a record when it is updated. See 'Versioning' for
                            # more details.
                           
KEEP_VERSIONS_AFTER_DELETION=
                            # Set this to True to retain all versions even after deletion.
                            # Trying to retrieve the resource will return a HTTP 404 error, and
                            # the activitystream will show the item as deleted, but the HTTP headers
                            # will still link to the Memento Timemap for the resource, where all previous
                            # versions will be available.

LOCAL_THESAURUS_URL=        # This entry is required if APPLICATION_NAMESPACE=local/thesaurus.
                            # It is the URL to the CSV file containing Local Thesaurus data
```

Using VS Code, it is possible to develop inside the container with full debugging and intellisence capabilities. Port `5001` is opened for remote debugging of the Flask application. For details see: https://code.visualstudio.com/docs/remote/containers

## Python Client (current v 2.1.1)

The LODGatewayClient in the `lodgatewayclient` package simplifies a lot of the API interaction with the LOD Gateway and can be pulled down from the Getty Nexus PyPi repository. 

Github: https://github.com/thegetty/lod-gateway-client

## Logging and Access logs

The logging configuration creates two `logging.StreamHandler` instances - one that will output all Python logger messages to `STDOUT`, and only `logging.CRITICAL` and `logging.ERROR` to `STDERR`. This is desired to make it easier to track fatal errors once deployed. This configuration is written to the root logger, and is inherited by any `logging` objects created subsequently. The log level is set using the `DEBUG_LEVEL` environment variable, and should be set to a standard Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`). The log levels are defined in order of severity, and run from left to right from least to most severe. What this means is that if the level is set to `DEBUG`, all messages marked `DEBUG` and more severe (all the way up to `CRITICAL` level) are logged. Set the level to `ERROR`, then only `ERROR` and more severe (only `CRITICAL` by default) messages are logged.

uWSGI hosts the Python application as a WSGI application. It pipes the `STDOUT` and `STDERR` messages as intended by the Python application. It also generates its own log messages relating to hosting the web service, both access request logs as well as health and service messages. The base configuration is defined in `source/web-service/uwsgi.ini`. Many other deployment-specific options can still be set using environment variables (such as `UWSGI_THREADS`, `UWSGI_PROCESSES`, etc.) at runtime, but the `.ini` file configures the baseline logging set-up.

### Log Routing:

**STDOUT**

- Python logger output? All levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.
- uWSGI messages? All messages.

**STDERR**

- Python logger output? `ERROR` and `CRITICAL` only.
- uWSGI messages? Only HTTP 50X messages (via a `log-route` match defined in `uwsgi.ini`)

## Versioning

If the `KEEP_LAST_VERSION` environment variable is present and set to `True`, the Versioning functionality is enabled and a subset of the [Memento specification](http://mementoweb.org/guide/rfc/#RFC6690) will be provided:
- A version of a resource will be created whenever the resource is updated with new data.
- The Memento-Datetime header will be included in all GET/HEAD requests for resources.
- Memento Timemaps are available for all resources, and are linked to in the Link header for all resource requests as specified.
  - The Timemap URIs are predictable from the resource URI: `http://host/namespace/resource_id` has a timemap at `http://host/namespace/-tm-/resource_id`
- Past versions of resources are linked to from the timemap, which is available in either `application/json` or `application/linked-format`. The `Accept` header of the request will be used for this content negotiation.
- The past versions are only available to authenticated clients. They include HTTP Link headers to the current version of the resource ('original'), and the timemap.
- The KEEP_VERSIONS_AFTER_DELETION affects deletion behaviour. If unset, or set to False, all old versions will be deleted when the current resource is deleted. If this is set to True, all versions will be retained even if the resource is deleted, and the history will be maintained if data for the resource is uploaded again.
- While not required in the specifications, the ordering of the resource and version links in the timemap will be in reverse chronological order, from newest to oldest. The first link will be the timemap, then the link to the original, and then the versions. This ordering is present in both the JSON and the application/link-format versions of the timemap.

Memento guidelines NOT IMPLEMENTED:
- Datetime content negotiation with the resource (`TimeGate` functionality)

Example HTTP Headers for a resource `GET /research/collections/place/c0380b6c-931f-11ea-9d86-068d38c13b76`:

```
HTTP/1.0 200 OK
Content-Type: application/json;charset=UTF-8
Content-Length: 527
Last-Modified: 2022-03-10T16:45:07
ETag: "9fc38eb8089641560326f35e1690897100af99ea9e5166ae56802735754ecd07:gzip"
Memento-Datetime: 2022-03-10T16:45:07
Link: <http://localhost:5100/research/collections/-tm-/place/c0380b6c-931f-11ea-9d86-068d38c13b76> ; rel="timemap"
Server: LOD Gateway/0.2
Vary: Accept-Encoding
Content-Encoding: gzip
Access-Control-Allow-Origin: *
Date: Thu, 10 Mar 2022 20:44:13 GMT
```

Example Timemap `GET /research/collections/-tm-/place/c0380b6c-931f-11ea-9d86-068d38c13b76` `(Accept: application/link-format)`

```
<http://localhost:5100/research/collections/-tm-/place/c0380b6c-931f-11ea-9d86-068d38c13b76>;rel="self";until="2022-03-10T16:45:07";from="2022-03-10T01:12:01+0000",
<http://localhost:5100/research/collections/place/c0380b6c-931f-11ea-9d86-068d38c13b76>;rel="original",
<http://localhost:5100/research/collections/-VERSION-/ea6871b2-a81a-44d8-851a-71df92ac1002>;datetime="2022-03-10T16:42:15+0000";rel="first memento",
<http://localhost:5100/research/collections/-VERSION-/0b068854-5486-4f6c-b559-6d1b6945e247>;datetime="2022-03-10T16:41:24+0000";rel="memento",
<http://localhost:5100/research/collections/-VERSION-/9703f9b7-2116-498f-8796-12555eacaec9>;datetime="2022-03-10T16:41:22+0000";rel="memento",
<http://localhost:5100/research/collections/-VERSION-/8c4af569-5d9c-4a36-bf83-7be7f34a38e7>;datetime="2022-03-10T01:12:01+0000";rel="last memento",
```

In JSON `GET /research/collections/-tm-/place/c0380b6c-931f-11ea-9d86-068d38c13b76` `(Accept: application/json)`

```
[
  {
    "uri": "http://localhost:5100/research/collections/-tm-/place/c0380b6c-931f-11ea-9d86-068d38c13b76",
    "rel": "self",
    "until": "2022-03-10T16:45:07",
    "from": "2022-03-10T01:12:01+0000"
  },
  {
    "uri": "http://localhost:5100/research/collections/place/c0380b6c-931f-11ea-9d86-068d38c13b76",
    "rel": "original"
  },
  {
    "uri": "http://localhost:5100/research/collections/-VERSION-/ea6871b2-a81a-44d8-851a-71df92ac1002",
    "datetime": "2022-03-10T16:42:15+0000",
    "rel": "first memento"
  },
  {
    "uri": "http://localhost:5100/research/collections/-VERSION-/0b068854-5486-4f6c-b559-6d1b6945e247",
    "datetime": "2022-03-10T16:41:24+0000",
    "rel": "memento"
  },
  {
    "uri": "http://localhost:5100/research/collections/-VERSION-/9703f9b7-2116-498f-8796-12555eacaec9",
    "datetime": "2022-03-10T16:41:22+0000",
    "rel": "memento"
  },
  {
    "uri": "http://localhost:5100/research/collections/-VERSION-/8c4af569-5d9c-4a36-bf83-7be7f34a38e7",
    "datetime": "2022-03-10T01:12:01+0000",
    "rel": "last memento"
  }
]
```

### ETags

Versioned resources will include an ETag header with a sha256 checksum in GET/HEAD request responses. The ETag complies with [RFC7232](https://datatracker.ietf.org/doc/html/rfc7232) in how the ETag is supplied and interacted with. The checksum value will be enclosed with double-quotes `"`, and if the resource is supplied with either gzip or deflate compression, the ETag will have `:gzip` or `:deflate` appended to the checksum as the specification requires.

The `If-Match` header is not currently supported.

The `If-None-Match` header IS supported for GET or HEAD requests. If a checksum is supplied, it will be checked against the requested resource if the resource exists. The checksum should be exact and not included any `:gzip/:deflate` suffix.
- If they match, it will respond with an HTTP 304 and empty body. 
- If they do not match (the resource is different compared to the local version), a normal HTTP 200 response is sent. 

The checksum type is sha256 and the algorithm is also part of the lodgatewayclient package [LODGatewayClient -> checksum_json()](https://github.com/thegetty/lod-gateway-client)

The code to create one outside of using the LODGatewayClient is as follows:

    import hashlib, json
    
    def checksum_json(json_obj):
        # Expects a JSON-serializable data structure to be passed to it.
        checksum = hashlib.sha256()
        # dump the object as JSON, with the sort_keys flag on to ensure repeatability
        checksum.update(json.dumps(json_obj, sort_keys=True).encode("utf-8"))
        return checksum.hexdigest()

## Functionality and Routes

Legend:  
"base_url" - application url (e.g. https://data.getty.edu)  
"ns" - application namespace (e.g. "museum/collection")  
"entity_type" - Entity type of the record. Can be an alias of an RDF type (e.g. "object" for Human Made Object)  

#### base_url/ns/health  

Returns OK if application is running and data base is accessible. Also checks the graph store health for instances that have ["PROCESS_RDF"] flag = "True". If one of the components is not running, Error 500 retuned.

#### base_url/ns/ingest

Method - POST. Authentication - 'bearer token'. Accepts a set of line-delimited records in JSON LD format. CRUD operations supported. When ingesting a record, the entity "id" should be relative, not a full URI. For example, when ingesting the record "Irises" into an LOD Gateway deployed at https://data.getty.edu/museum/collection, the entity "id" should be "object/c88b3df0-de91-4f5b-a9ef-7b2b9a6d8abb" producing the following URI in the deployed application: https://data.getty.edu/museum/collection/object/c88b3df0-de91-4f5b-a9ef-7b2b9a6d8abb  

In the case of a 'delete' operation, only the data part is deleted. A record remains in the database that indicates that the record existed and its lifecycle is recorded in the activity stream. A record delete operation is done by ingesting a JSON record with the relevant entity id and a single key/value pair, `"_delete": "true"`.  

When records are ingested into the LOD Gateway, they are also expanded into RDF and added to the graph store if a valid context is given and the ["PROCESS_RDF"] flag = "True". Atomic processing is implemented, i.e. if one of the records fails or the RDF expansion operations are unsuccessful, the entire transaction is rolled back.

#### base_url/ns/entity_type/entity_id

Return a single record with id = <entity_type/entity_id>. If record is not found, Error 404 returned.

#### base_url/ns/entity_type/entity_id/activity-stream

Return activity stream for a single record with id = <entity_type/entity_id>

#### base_url/ns/activity-stream

Return activity stream for the whole data set broken into pages of no greater than a defined number of activity items. Currently it is set 100.

#### base_url/ns/activity-stream/type/entity_type

Return activity stream for a specific 'entity_type'. Examples of entity types from LOD 'museum/collection' - 'Group', 'Person', 'HumanMadeObject', etc. The same pagination structure implemented as for the main 'activity-stream'.

#### base_url/ns/sparql

SPARQL endpoint for querying RDF triples representation of data stored in the LOD Gateway. No authentication is required.

#### base_url/ns/sparql-ui

YASGUI implementation of a user interface for doing SPARQL queries on the data stored in an individual instance of an LOD Gateway.


## Technical Architecture

The LOD Gateway project consists of the following primary software components:

- [Python](https://www.python.org) version 3.7+
- [Flask](http://flask.pocoo.org)
- [SQLAlchemy](https://www.sqlalchemy.org)
- [PyLD](https://github.com/digitalbazaar/pyld)

## License and Copyright Information

Copyright © The J. Paul Getty Trust 2019.

The Getty name, logos, and trademarks are owned by the J. Paul Getty Trust, and subject to [the J. Paul Getty Trust Trademark Policy for Open Source Projects](https://www.getty.edu/legal/trademarks/opensource.html).
