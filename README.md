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

VERSIONING_AUTHENTICATION=  # if True, authentication required for versioning
                            # if missing in .env, default value True will be set in the app

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
                            
RDF_BASE_GRAPH=             # Requires PROCESS_RDF to be set to true to have any effect. The value should be
                            # the entity id of a resource that will be used as the 'base graph' for the LOD Gateway.
                            # Any triples in the base graph will be added to the graph store, but these triples
                            # will be removed from any other RDF resources before they are added to the graph store

RDF_CONTEXT_CACHE=          # A JSON-encoded value that holds a context cache to preload into the PyLD document loader
                            # It should be in the form: {"url": context object, ...} with the context object as follows:
                            # context object -> {"document": context document, "expires": None/datetime, "contextUrl": None, "documentUrl": None}

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

SUBADDRESSING=
                            # True or False (default). This enables the subaddressing check for identifiers
                            # that may be within other resources. 
                            
                            SUBADDRESSING_MIN_PARTS - smallest number of (path) parts to consider when resolving a 
                                                      subaddressed path to a parent entity (default: 1)
                            SUBADDRESSING_MAX_PARTS - largest number of (path) parts to consider when resolving a 
                                                      subaddressed path to a parent entity (default: 4)
```

Using VS Code, it is possible to develop inside the container with full debugging and intellisence capabilities. Port `5001` is opened for remote debugging of the Flask application. For details see: https://code.visualstudio.com/docs/remote/containers

## Python Client (current v 2.3.0)

The LODGatewayClient in the `lodgatewayclient` package simplifies a lot of the API interaction with the LOD Gateway and can be pulled down from the Getty Nexus PyPi repository. 

Github: https://github.com/thegetty/lod-gateway-client

## Server Capabilitiess

The LOD Gateway has a set of additional functionality that can be turned on (through the environment variables mentioned above). Each response will include an `X-LODGATEWAY-CAPABILITIES` header that will include a brief summary of which are enabled, and may also include the URI for the base graph, if base graph filtering is enabled. For example:

```
X-LODGATEWAY-CAPABILITIES: JSON-LD: 'True', Base Graph: 'http://localhost:5100/museum/collection/_basegraph', Subaddressing: 'True', Versioning: 'True'
```
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

## Sub-addressing

Turning this on by setting the environment variable `SUBADDRESSING` will allow the LOD Gateway to check to see if a given requested entity is within a parent document and to return the section of the data that corresponds to it.

  - Must be hierarchically named (prefixed by the id path of the parent object eg 'document/1')
  - Not supported on old versions of documents (retrieved via Memento, see Versionin)
  - HTTP Location response header will have the full URI to the parent resource which it was drawn from

For example:

```
LOD Gateway -> https://lodgateway/namespace

Upload:

{
    "@context": "https://linked.art/ns/v1/linked-art.json",
    "id": "place/c0380b6c-931f-11ea-9d86-068d38c13b76",
    "identified_by": [
        {
            "classified_as": [
                {
                    "_label": "thoroughfare names",
                    "id": "http://vocab.getty.edu/aat/300419273",
                    "type": "Type",
                }
            ],
            "content": "Sunset Boulevard",
            "id": "place/c0380b6c-931f-11ea-9d86-068d38c13b76/name",
            "type": "Name",
        },
    "type": "Place",
}
```


Resolving `https://lodgateway/namespace/place/c0380b6c-931f-11ea-9d86-068d38c13b76/name` should result in something like the following:


HTTP Response:

```
Access-Control-Allow-Origin: *
Content-Length: 264
Content-Type: application/json;charset=UTF-8
ETag: "abc1fba295f1b6aa146cc3417d7a00dff9be0f8593ff0d07104d24f2cd9ef845"
Last-Modified: 2021-08-27T09:07:49
Link: <https://lodgateway/namespace/-tm-/place/c0380b6c-931f-11ea-9d86-068d38c13b76>; rel="timemap"; type="application/link-format" , <https://lodgateway/namespace/-tm-/place/c0380b6c-931f-11ea-9d86-068d38c13b76>; rel="timemap"; type="application/json" , <https://lodgateway/namespace/place/c0380b6c-931f-11ea-9d86-068d38c13b76>; rel="original timegate"
Location: https://lodgateway/namespace/place/c0380b6c-931f-11ea-9d86-068d38c13b76
Server: LOD Gateway/2.3.0
X-LODGATEWAY-CAPABILITIES: "JSON-LD: 'True', Base Graph: 'http://localhost:5100/museum/collection/_basegraph', Subaddressing: 'True', Versioning: 'True'"
Vary: accept-datetime, Accept-Encoding


 {
    "content": "Sunset Boulevard",
    "id": "https://lodgateway/namespace/place/c0380b6c-931f-11ea-9d86-068d38c13b76/name",
    "type": "Name",
     "classified_as": [
        {
            "_label": "thoroughfare names",
            "id": "http://vocab.getty.edu/aat/300419273",
            "type": "Type",
        }
    ],
}
```

Subaddressing starts by searching from the max length to the minimum. For example:

```
entity 'a/b/c/d/e/f/g/h/i' does not exist as a record. Max/min are at defaults:

Search for 'a/b/c/d/e/f/g/h/i' in the following records if they exist:
    a/b/c/d
    a/b/c
    a/b
    a
    
The search will stop as soon as it finds a valid record, and will return either the part of the document that matches, or HTTP 404
```

## RDF formats

If RDF processing is enabled, the resources will be treated as valid JSON-LD documents. Alternate formats of the RDF data can be requested by either using an Accept header with an allowed mimetype, or using a 'format' GET url parameter to specify the format:

| MIME type            | format   |
| ---------------      |----------|
| applicaton/ntriples  | nt       |
| text/turtle          | turtle   |
| application/rdf+xml  | xml      |
| application/ld+json  | json-ld (default) |
| text/n3              | n3  |
| application/n-quads  | nquads  |
| application/trig     | trig  |

Browsers do not handle a number of these text-based formats, and will assume that the user wants to download them. To force the response Content-Type to be text/plain to enable the browser to show them, set the URL get parameter "force-plain-text" to be "true". NB These formats will be UTF-8 encoded.

Examples:

If there was a resource 'object/1' in the LOD Gateway 'http://lodgateway/collection/':

```
GET http://lodgateway/collection/object/1    --> JSON-LD

GET http://lodgateway/collection/object/1&format=nt    --> ntriples, "Content-Type: application/n-triples"
GET http://lodgateway/collection/object/1&format=nt&force-plain-text=true    --> ntriples, "Content-Type: text/plain"
```

Or via Accept header:
```
$ curl -i -H "Accept: application/rdf+xml" http://lodgateway/collection/object/1
HTTP/1.1 200 OK
Content-Type: application/rdf+xml
Content-Length: 44775
Last-Modified: 2022-11-28T23:14:28
ETag: "8b6bfe250f3bbc4fa5b0f797036bea93be25f003bb9571afa87fdb43d27ff8df"
Link: <http://lodgateway/collection/-tm-/object/1>; rel="timemap"; type="application/link-format" , <http://lodgateway/collection/-tm-/object/1>; rel="timemap"; type="application/json" , <http://lodgateway/collection/object/1>; rel="original timegate"
Vary: accept-datetime, Accept-Encoding
Server: LOD Gateway/2.3.0
Access-Control-Allow-Origin: *

<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF
   xmlns:crm="http://www.cidoc-crm.org/cidoc-crm/"
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:dcterms="http://purl.org/dc/terms/"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
   xmlns:skos="http://www.w3.org/2004/02/skos/core#"
>
  <rdf:Description rdf:about="http://vocab.getty.edu/aat/300053588">
    <rdf:type rdf:resource="http://www.cidoc-crm.org/cidoc-crm/E55_Type"/>
    <rdfs:label>Object-Making Processes and Techniques</rdfs:label>
    
    ...
```

## RDF Processing

If PROCESS_RDF is set to true, then the LOD Gateway will connect to a SPARQL Update 1.1 compliant endpoint and synchronize resources uploaded to the gateway with this endpoint. It will turn the JSON-LD into RDF triples, and associate them with a named graph linked to the top 'id' or '@id' of the resource. If the resource is removed from the LOD Gateway, its triples are also removed.

It is required that if PROCESS_RDF is set to true, `SPARQL_QUERY_ENDPOINT` and `SPARQL_UPDATE_ENDPOINT` are set to the URLs of the SPARQL services mentioned, as well as `RDF_NAMESPACE` which is used to determine the named graph URIs for the resources. These URIs are generated from concatenating the environment variable `BASE_URL` with `RDF_NAMESPACE` and adding the resource's `@id`/`id` to the end.

For example, if a JSON-LD document has an `@id` of `foo`, and is uploaded to an LOD Gateway with `BASE_URL` `https://localhost:8000` and `RDF_NAMESPACE` `test`, the named graph URI would be `<https://localhost:8000/test/foo>`.

If the JSON-LD is a `@graph`, the named graph part of its RDF will be overwritten by the LOD Gateway's named graph URI before updating the graph store. It will not change the JSON-LD stored, but it will force the triples present to be in a single named graph.

### RDF Refresh

It may be required to update a graph store with the JSON-LD stored in the LOD Gateway. For example, the graph store is new and empty, or the named graph has been removed or altered by some other method (like a direct SPARQL update) rather than using the LOD Gateway. This can be done through the 'ingest' route, by passing a JSON message of the form `{"id": "entity_id", "_refresh": true}` for a given entity_id (the relative '@id'/'id' value, not the full FQDN).

### RDF Base Graph

If the env variable "RDF_BASE_GRAPH" is set to an entity id (eg '_basegraph'), this document will be used as the **base graph**. The base graph is a set of triples that will be removed from any named graph RDF added to the graph store by the LOD Gateway. The base graph triples will be added to the graph store, so they will be present in the union graph. However, they will not be present in any individual named graph, besides the named graph corresponding to the base graph.


    - The JSON-LD document will be unaffected
    - Union graph SPARQL queries should be unchanged
    - BUT queries against specific named graphs will be affected (but querying them specifically is not a use case)

This functionality provides a toolset to deal with the issue of replicated triples between named graphs. Providing a human-readable "_label" to an AAT term may seem innocuous, but the same triple may be present in every named graph, and some of the L2 gateways can have millions of named graphs.

Changing the base graph will **not** change the named graphs stored in the graph store retrospectively. The base graph will be updated in the graph store, and the application should be restarted to ensure that all web workers reload with the updated triple filter set (workers will be reloaded every 1000 or so requests, but to be safe, restarting manually is recommended). To update the graph store, it will be necessary to run a `_refresh` command against all the resources that should be updated in the graph store.

## Default base graph

Any triples that are recorded in the JSON-LD will be used as the set of triples to filter from other documents. The named graph part of any quads will be discarded and replaced by the URI of the base graph in the same way that that part would be for any other uploaded document.

A default empty base graph will be added if one does not already exist, and the filter set of its triples will be loaded from this resource when the instance starts up. Changing the base graph is done in the same way as uploading any other document to the LOD Gateway. It only needs to be a parsable JSON-LD document, and have the base graph relative ID.

Using a [named graph](https://www.w3.org/TR/json-ld11/#named-graphs]) in JSON-LD with @graph is a useful container for triples that may or may not relate to one another.

For example:

```
{
    "@context": {
        "dc": "http://purl.org/dc/elements/1.1/",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "_label": {"@id": "rdfs:label"},
    },
    "@id": "_basegraph",
    "@graph": [
        {"@id": "urn:test1", "_label": "nothanks"},
        {"@id": "urn:test2", "_label": "nothanksagain"},
    ],
}
```

Here, the @graph container holds two unrelated triples which will be used for the filter, and a context can be used to make the document easier to read as normal: 

```
<urn:test1> <rdfs:label> "nothanks" .
<urn:test2> <rdfs:label> "nothanksagain" .
```

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

Example HTTP Headers for a resource `GET /research/collections/place/c0380b6c-931f-11ea-9d86-068d38c13b76`:

```
HTTP/1.0 200 OK
Content-Type: application/json;charset=UTF-8
Content-Length: 527
Last-Modified: 2022-03-10T16:45:07
ETag: "9fc38eb8089641560326f35e1690897100af99ea9e5166ae56802735754ecd07:gzip"
Memento-Datetime: 2022-03-10T16:45:07
Link: <http://localhost:5100/research/collections/-tm-/place/c0380b6c-931f-11ea-9d86-068d38c13b76> ; rel="timemap"
Server: LOD Gateway/2.3.0
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

If the LOD Gateway is configured to process RDF, then there is an additional ingest procedure available: `refresh`. This refreshes the triplestore with a record's RDF (expanded from the JSON-LD). This is useful when the triplestore is out of sync with the contents of the LOD Gateway for some reason (directly updated in error, or starting a new triplestore backend from scratch). This works in the same manner as the `delete` procedure - to refresh an id "entity_id", the ingest JSON line should be `{"id": "entity_id", "_refresh": true}`. A successful response will include the entity_id in the JSON response, with a value of "refreshed" or "deleted" (should the entity_id not have data or not exist). If PROCESS_RDF is not turned on, the response will be "rdf_processing_is_off".

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
