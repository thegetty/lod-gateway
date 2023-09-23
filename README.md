![LOD Gateway](documentation/logo.png)

# LOD Gateway

This repository contains the source code for the LOD Gateway – a fast and reliable Linked Open Data (LOD) document store with integrated graph expansion and associated graph storage and graph query features.

The LOD Gateway offers the following key functionality:

 * stores and provides access to [JSON](https://www.json.org/json-en.html) and [JSON-LD](https://www.w3.org/TR/json-ld11/) documents via a simple [REST API](https://www.ibm.com/topics/rest-apis) interface;
 * optionally stores previous versions of records, and makes these available via a [Momento](https://www.rfc-editor.org/rfc/rfc7089.txt) compliant API;
 * provides an [Activity Streams](https://www.w3.org/TR/activitystreams-core/) compliant change history so that changes to documents are discoverable by external systems;
 * offers optional integration with a graph store such as [Fuseki](https://jena.apache.org/documentation/fuseki2/), [GraphDB](https://graphdb.ontotext.com) or [Neptune](https://aws.amazon.com/neptune/), which extends the functionality of the Gateway making it possible to perform graph queries against the stored JSON-LD documents using the [SPARQL](https://www.w3.org/TR/sparql11-query/) query language.

The LOD Gateway can be used in a number of different ways out-of-the-box depending on how its settings are configured:

 * as a JSON-LD document store with graph features enabled
 * as a JSON-LD document store without graph features enabled
 * as a JSON document store (where the graph features do not apply)

When the LOD Gateway is configured as a JSON-LD store with graph features enabled, JSON-LD documents submitted to the Gateway will be both stored by the LOD Gateway for later retrieval, and the document will also be expanded into RDF according to the `@context` document referenced within the JSON-LD, with the resultant [RDF](https://www.w3.org/RDF/) [triples](https://en.wikipedia.org/wiki/Semantic_triple) being stored in the associated graph store for querying and retrieval via the LOD Gateway's SPARQL endpoint or [YASGUI](https://triply.cc/docs/yasgui/)-powered SPARQL UI.

The **Configuration** section below details the settings offered by LOD Gateway and how to configure them as needed.


## Setup Instructions

The LOD Gateway has been developed using [Python](http://python.org) and [Docker](https://www.docker.com) for ease of ongoing development and deployment.

_These instructions assume that you have [Docker Desktop](https://www.docker.com/products/docker-desktop) installed on your computer. If not, please follow the aforementioned Docker Desktop link for instructions on installing Docker Desktop and the Docker Compose plugin, before proceeding with the setup steps below. For installation of LOD Gateway on a server, the [Docker Engine](https://docs.docker.com/engine/) or another Docker-compatible runtime should be available on the server for which installation instructions and tutorials are readily available online relevant to your deployment environment._


### Components

The LOD Gateway contains one production container: `web`; and for development purposes, includes a containerized instance of the [PostgreSQL](http://postgresql.org) relational database server, available as the `postgres` service, and a containerized instance of the Fuseki graph store, included as the `fuseki` service. For more information on the overall architecture of the application and the major software libraries used by the LOD Gateway, see the **Technical Architecture** section below.

In a typical staging or production environment the LOD Gateway will usually be configured to use a separate PostgreSQL database server and separate graph store, rather than using the containerized instances of these two services. For development purposes using the bundled containerized database and graph store works really well and makes it easy to get an instance of LOD Gateway up-and-running for development purposes as well as for learning and experimentation.


### Obtaining the Source Code, Building the Containers & Running the LOD Gateway

To get started with the LOD Gateway, we can spend a few minutes cloning the source code repository, making a copy of the example configuration file, building the Docker containers, and starting up the application by running the following commands in sequence:

    $ git clone https://github.com/thegetty/lod-gateway
    $ cd lod-gateway
    $ cp .env.example .env
    $ docker compose build
    $ docker compose up --detach

To view the logs of the application while it is running, enter the following command:

	$ docker compose logs --follow

To shut the application down, enter the following command:

    $ docker compose down

Once running, the LOD Gateway instance will be available by default on your host computer at `http://localhost:5100` – and you can visit this URL in a web browser or a HTTP REST Client to start interacting with the LOD Gateway. If you wish to modify the port number from the default of `5100`, you can do so by modifying the relevant variable in the `.env` file, `FLASK_RUN_PORT`, and restarting the application. See the **Configuration** section below for more details.

**Please Note**: When creating an instance of the LOD Gateway application for the first time, the Gateway's required database schema must be manually created by running the provided database setup command as illustrated below. Assuming that the proper database connection settings have been defined in the `.env` file (if you are using the default setup without changes, it will be), the database schema can be created by running the following commands:

If the LOD Gateway isn't already running on your computer, run the startup command first:

	$ docker compose up --detach

Then from the host computer's command line, run the following `exec` command, which will provide access to the command line within the running `web` service container:

    $ docker compose exec web bash

Then from the container's command line, which appears after running `docker compose exec`, run the following command to generate the database schema:

    $ flask db upgrade

Alternatively, the above two commands may be combined and executed entirely from the host computer's command line as follows:

    $ docker compose exec web flask db upgrade


## LOD Gateway API & Web Interfaces
The LOD Gateway provides a REST API which is the primary method of interaction, as well as a lightweight web interface that provides a landing page and Dashboard for the Gateway. More information regarding these two interfaces may be found below in the **API Functionality & Routes** and **Web Interface** sections below.


## API Functionality & Routes

The following legend details the placeholder names used in the route descriptions and documentation below:

 * `{base-url}` – the application base URL (e.g. `https://data.getty.edu`)
 * `{namespace}` – the application namespace (e.g. `museum/collection`)
 * `{entity-type}` – the entity type of a record which may be an alias of an RDF type (e.g. `object` for `HumanMadeObject`)
 * `{entity-id}` – the unique ID of a record (e.g. `c88b3df0-de91-4f5b-a9ef-7b2b9a6d8abb`)
 * `{entity-uri}` – the entity URI is a combination of the `{entity-type}` and `{entity-id}` for a record, for example `object/c88b3df0-de91-4f5b-a9ef-7b2b9a6d8abb`.

⚠️ _**Please Note**: API operations listed below that require authentication will be marked with a key 🗝️ symbol. When marked, a HTTP request `Authorization` header MUST be submitted as part of the HTTP request, and the `Authorization` header must have a value of `Bearer {token}` where `{token}` is the value configured in the `AUTHORIZATION_TOKEN` environment variable (see the **Configuration** section below for more information on configuring the LOD Gateway)._ If the `Authorization` header is absent when it is required by an API operation or if the header is present but it's value is incorrect, the LOD Gateway will respond with a `401 Unauthorized` HTTP response status code.


#### HTTP GET {base-url}/{namespace}/health

The `/health` endpoint provides a means for checking the current "health" of the application. If the application is running, and if the database (and where relevant, the graph store) is accessible, the endpoint will return a `200 OK` HTTP response, otherwise if either the database (or where relevant, the graph store) is offline or is temporarily inaccessible, the endpoint will return a `500 Internal Server Error` HTTP response.

#### HTTP POST {base-url}/{namespace}/ingest 🗝️

The `/ingest` endpoint accepts one or more line-delimited record strings in JSON or JSON-LD format.

When ingesting records into the LOD Gateway, any top-level `"id"` properties in the records, or any nested `"id"` properties within the records that reference other documents held in the same instance of the Gateway MUST use relative URI values, rather than absolute URI values. When referencing records held within other systems, one MUST use absolute URIs for those `"id"` values.

For example, when ingesting the record for Vincent van Gogh's _Irises_ (1889) into an LOD Gateway instance deployed at `https://data.getty.edu/museum/collection`, the `"id"` property MUST have an `"id"` value with a relative URI of `"object/c88b3df0-de91-4f5b-a9ef-7b2b9a6d8abb"` resulting in the Gateway serving the record via the absolute URI of `https://data.getty.edu/museum/collection/object/c88b3df0-de91-4f5b-a9ef-7b2b9a6d8abb`. The Gateway will also insert the URL prefix into the `"id"` values before returning the response, converting any relative URIs in the document to absolute URIs that can be resolved by downstream systems.

The following code sample illustrates ingesting a record into an LOD Gateway instance, including how to supply the `Authorization` header, how to prepare the line-delimited `POST` body containing one or more serialized JSON/JSON-LD strings, and how if desired to submit multiple records as part of a single request:

```
#!/usr/bin/env python3

# We make use of the popular Python `requests` library here.
# This can be installed using `pip` via `pip install requests`
# See https://pypi.org/project/requests/ for more information.
import requests
import json

# This is the URL of the LOD Gateway instance being used,
# here we point to the default localhost installation:
url = "http://localhost:5100/museum/collection/ingest"

# The Authorization header's Bearer value must match the
# AUTHORIZATION_TOKEN environment variable value for the
# LOD Gateway instance, which by default is 'AuthToken':
headers = {
	"Authorization": "Bearer AuthToken",
}

# Here is a sample JSON-LD record, illustrating the use of
# relative URIs for "id" properties referencing records in
# this LOD Gateway and absolute URIs for resources managed
# and provided by external services, such as Vocab URIs:
artwork = {
	"@context": "https://linked.art/ns/v1/linked-art.json",
	"id": "object/1234",
	"type": "HumanMadeObject",
	"_label": "Example Painting",
	"classified_as_as": [
		{
			"id": "http://vocab.getty.edu/aat/300133025",
			"type": "Type",
			"_label": "Work of Art"
		},
		{
			"id": "http://vocab.getty.edu/aat/300033618",
			"type": "Type",
			"_label": "Painting"
		}
	],
	"current_location": {
		"id": "place/5678",
		"type": "Place",
		"_label": "Gallery #1"
	}
}

# Here is the referenced sample Place record:
place = {
	"@context": "https://linked.art/ns/v1/linked-art.json",
	"id": "place/5678",
	"type": "Place",
	"_label": "Gallery #1",
}

# Add any records being submitted as part of the same request
records = [artwork, place]

# Convert the records into line-delimited JSON strings
data = "\n".join([json.dumps(record) for record in records])

# Submit the record data to the LOD Gateway instance for storage:
response = requests.post(url=url, headers=headers, data=data)

# Do something with the response
print("code: %s" % (response.status_code))
print("data: %s" % (response.json()))
```

#### Ingest Operations: Delete 🗝️

In addition to inserting or updating records, the `/ingest` endpoint provides support for deleting existing records by passing a record's relative URI along with a special `"_delete"` key having a value of `true` (or `"true"` or `"True"`). For example to delete a record with a relative URI of `place/5678` in the current LOD Gateway, create a JSON string like this: `{"id": "place/5678", "_delete": true}` and submit it to the `/ingest` endpoint. Delete requests may be combined with other `/ingest` endpoint operations, such as along side other records that are being inserted, updated, deleted, or refreshed, and may be submitted as part of one `POST` request to the `/ingest` endpoint, or they may be submitted individually as a series of `POST` requests to the `/ingest` endpoint if preferred.

The example code below uses the `/ingest` endpoint to delete `place/5678`:

```
import requests
import json

# This is the URL of the LOD Gateway instance being used,
# here we point to the default localhost installation:
url = "http://localhost:5100/museum/collection/ingest"

# All requests to the `/ingest` endpoint MUST provide authorization:
headers = {
	"Authorization": "Bearer AuthToken",
}

# A delete request only requires the top-level record ID as a relative
# URI value and the special `_delete` key with a `True` value:
delete = {
	"id": "place/5678",
	"_delete": True,
}

# When submitting a single record to LOD Gateway's `/ingest` endpoint
# we can just submit the JSON serialized string as the data value;
# regardless of which programming language you are using to interface
# with the LOD Gateway, ensure that a compact JSON serialization is
# used, that lacks any extraneous indentation or line-breaks used
# solely for formatting the structure of the document. In Python that
# means calling `json.dumps` without passing the `indent` parameter.
data = json.dumps(delete)

response = requests.post(url=url, headers=headers, data=data)
```

In order to help maintain the change history of records within the LOD Gateway, the Gateway always performs "soft" deletes where only the record's data (the stored JSON or JSON-LD value) is deleted. The record's metadata remains in the database to indicate that the record existed and its deletion is recorded in the Activity Stream. When an LOD Gateway has graph functionality enabled, a delete operation will delete the record's associated named graph from the graph store.

A successful response will include the `{entity-uri}` in the JSON response, with a value of `"deleted"`.

An example HTTP response body will look similar to the following:

```
{"object/1234": "deleted"}
```


#### Ingest Operations: Refresh 🗝️

When an LOD Gateway has graph functionality enabled, the `/ingest` endpoint also supports refreshing the graph store using the JSON-LD records already stored in the Gateway.

The "refresh" operation refreshes the graph store with a record's RDF (expanded from the existing JSON-LD). This is useful when the graph store is out of sync with the contents of the LOD Gateway, for example where one or more records in the graph store were directly updated in the graph store in error, or when migrating the existing data to a new graph store from scratch. Being able to reload the graph store from the existing JSON-LD could save considerable time if generating the JSON-LD is a time consuming process.

To refresh a record, use the special `"_refresh"` key with a value of `true` (or `"true"` or `"True"`). For example to refresh a record with a relative URI of `object/1234` in the current LOD Gateway, create a JSON string like this: `{"id": "object/1234", "_refresh": true}` and submit it to the `/ingest` endpoint. Refresh requests may be combined with other `/ingest` endpoint operations, such as along side other records that are being inserted, updated, deleted, or refreshed, and may be submitted as part of one `POST` request to the `/ingest` endpoint, or they may be submitted individually as a series of `POST` requests to the `/ingest` endpoint if preferred.

A successful response will include the `{entity-uri}` in the JSON response, with a value of `"refreshed"` or `"deleted"` (in cases where the `{entity-uri}` did not have any data or where the record did not exist). If graph functionality for the LOD Gateway is not currently enabled, the response will be `"rdf_processing_is_off"`.

An example HTTP response body will look similar to the following:

```
{"object/1234": "refreshed"}
```

#### Ingest Functionality: Atomic Operations

Calls the `/ingest` endpoint are always atomic in nature, and if one or more of the provided records cannot be stored, the operation will be rolled back. When an LOD Gateway has graph functionality enabled, the provided JSON-LD records are expanded into RDF if a valid `@context` is referenced within the JSON-LD, and are then saved to the graph store. If storing any of the records fails or if any of the RDF expansion or storage steps are unsuccessful, the entire transaction will be rolled back. This is useful when you want to ensure that a related set of records have either all been successfully stored/updated in the Gateway, or that none of them did, rather than potentially encountering a situation where there are inconsistencies in the data because only part of the ingest request was successful.

#### HTTP GET {base-url}/{namespace}/{entity-type}/{entity-id}

Returns a single record with the `{entity-uri}` equal to `{entity-type}/{entity-id}`. If record does not exist in the LOD Gateway, or has been previously (soft) deleted, the HTTP response status code, `404 Not Found`, will be returned instead.

#### HTTP GET {base-url}/{namespace}/{entity-type}/{entity-id}/activity-stream

Returns the Activity Stream for a single record with the `{entity-uri}` equal to `{entity-type}/{entity-id}`.

#### HTTP GET {base-url}/{namespace}/activity-stream

Returns the Activity Stream for the entire data set, divided into pages containing no more than the defined number of Activity Stream items per page. By default the maximum number of Activity Stream items per page is 100 (see the **Configuration** section below for more information).

#### HTTP GET {base-url}/{namespace}/activity-stream/type/{entity-type}

Returns the Activity Stream for a specific `{entity-type}`. Examples of entity types from the Museum Collection LOD Gateway available at `https://data.getty.edu/museum/collection` include: `group`, `person`, `object`, `exhibition`, etc. The same paginated interaction and response structure is implemented as for the main Activity Stream endpoint at `{base-url}/{namespace}/activity-stream`.

#### HTTP GET {base-url}/{namespace}/sparql

The `/sparql` endpoint supports performing SPARQL queries directly against the data stored in the LOD Gateway's associated graph store. No authentication is required, but graph functionality MUST be enabled for the LOD Gateway instance, otherwise a `501 Not Implemented` HTTP response status code will be returned.

#### HTTP GET {base-url}/{namespace}/sparql-ui

The `/sparql-ui` endpoint provides a YASGUI implementation which offers a web-based user interface for performing SPARQL queries against the data stored in the LOD Gateway. No authentication is required, but graph functionality MUST be enabled for the LOD Gateway instance, otherwise a `501 Not Implemented` HTTP response status code will be returned.

## Web Interface

The LOD Gateway provides a lightweight web interface offering a landing page and a dashboard for each instance, providing useful information about the contents of the LOD Gateway instance and links to various related resources. To access the dashboard for any LOD Gateway instance visit the following URL in a web browser from a computer that has network access to the LOD Gateway instance you wish to visit:

#### HTTP GET {base-url}/{namespace}/dashboard

Upon visiting the LOD Gateway's dashboard, you should see something similar to the following:

![LOD Gateway's Dashboard](documentation/dashboard.png)

The dashboard provides a summary of the entity counts of the documents stored in the system, as well as a total count of the stored records and the total count of record changes. Links to the Activity Stream, SPARQL API endpoint and SPARQL GUI are also provided. Custom links may be added to the dashboard page if desired by customizing the value of the `LINK_BANK` environment variable, such as links to documentation about the data sets stored in the LOD Gateway (see the **Configuration** section below for more information).


## Server Capabilities

As described in this documentation, the LOD Gateway offers additional functionality that can be enabled through environment variables. To assist downstream clients in determining which additional functionality is available, each response will include an `X-LODGATEWAY-CAPABILITIES` HTTP response header that includes a brief summary of which functionality has been enabled, and may also include the URI for the base graph, if base graph filtering has been enabled.

Depending upon the Gateway's current configuration, the header will look something like the following:

```
X-LODGATEWAY-CAPABILITIES: JSON-LD: 'True', Base Graph: 'http://localhost:5100/museum/collection/_basegraph', Subaddressing: 'True', Versioning: 'True'
```

## Logging & Access Logs

The logging configuration creates two `logging.StreamHandler` instances – one that will output all Python logger messages to `STDOUT`, and only `logging.CRITICAL` and `logging.ERROR` level messages to `STDERR`. This is desired to make it easier to track fatal errors once deployed. This configuration is written to the root logger, and is inherited by any `logging` objects created subsequently. The log level is set using the `DEBUG_LEVEL` environment variable, and should be set to a standard Python log level value (`DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`). The log levels are defined in order of severity, and run from left to right from least to most severe. What this means is that if the level is set to `DEBUG`, all messages marked `DEBUG` or more severe (all the way up to `CRITICAL` level) are logged. When setting the level to `ERROR`, only `ERROR` or more severe messages (only `CRITICAL` by default) are logged.

Gunicorn hosts the Python application as a WSGI application. It pipes the `STDOUT` and `STDERR` messages as intended by the Python application. It also generates its own log messages relating to hosting the web service, access request logs as well as health and service messages.

### Log Routing

**STDOUT**

- Python logger output? All levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.
- Gunicorn messages? All messages.

**STDERR**

- Python logger output? `ERROR` and `CRITICAL` only.
- Gunicorn messages? Only HTTP 50X messages by default.

## Sub-Addressing

When sub-addressing has been enabled (via the environment variable `SUBADDRESSING`), the LOD Gateway provides support for checking if a requested sub-addressed node exists within a parent document, and if so, the Gateway will return the relevant section of the data that corresponds to the sub-address:

 * The node MUST be hierarchically identified; that is, its `"id"` value must be prefixed by the `"id"` path of the parent record, e.g. `document/1/node` where `document/1` is the parent record's `"id"`. The node MUST also be contained within the same document.
 * Sub-addressing requests are not supported against prior versions of documents (those retrieved via Memento, see the **Versioning** section below for more information).
 * The HTTP `Location` response header will be populated with the full URI of the parent resource from which the sub-addressed node was retrieved.

For example, assuming the following JSON-LD document has been ingested into an LOD Gateway instance at:
`https://lodgateway/namespace/place/c0380b6c-931f-11ea-9d86-068d38c13b76`:

```
{
    "@context": "https://linked.art/ns/v1/linked-art.json",
    "id": "place/c0380b6c-931f-11ea-9d86-068d38c13b76",
    "type": "Place",
    "identified_by": [
        {
            "id": "place/c0380b6c-931f-11ea-9d86-068d38c13b76/name",
            "type": "Name",
            "classified_as": [
                {
                    "id": "http://vocab.getty.edu/aat/300419273",
                    "type": "Type",
                    "_label": "thoroughfare names"
                }
            ],
            "content": "Sunset Boulevard"
        }
    ]
}
```

Resolving `https://lodgateway/namespace/place/c0380b6c-931f-11ea-9d86-068d38c13b76/name` should result in a HTTP response similar to the following being returned:

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
    "id": "https://lodgateway/namespace/place/c0380b6c-931f-11ea-9d86-068d38c13b76/name",
    "type": "Name",
     "classified_as": [
        {
            "id": "http://vocab.getty.edu/aat/300419273",
            "type": "Type",
            "_label": "thoroughfare names"
        }
    ],
    "content": "Sunset Boulevard"
}
```

Sub-addressing requests search from the maximum length to the minimum. For example, when entity `a/b/c/d/e/f/g/h/i` does not exist as a standalone record, and the maximum/minimum are at their defaults, the search for `a/b/c/d/e/f/g/h/i` will be performed against the following records if they exist:

```
a/b/c/d
a/b/c
a/b
a
```

The search will stop as soon as it finds a valid match, and the request will return either the relevant sub-addressed node of the document that matched, or a HTTP `404 Not Found` response.

## RDF Formats

If graph functionality, and therefore RDF processing is enabled, the ingested resources will be treat as valid JSON-LD documents. Alternate formats of RDF data may be requested from the LOD Gateway either by including a HTTP request `Accept` header with a supported MIME type, using one of the values from the "MIME Type" column of the table below, or by supplying a `format` GET query string parameter to specify the format, using one of the values from the "Format" column in the table below:

| MIME Type            | Format            | Notes |
| -------------------- | ----------------- | ----- |
| application/ntriples | nt                |       |
| text/turtle          | turtle            |       |
| application/rdf+xml  | xml               |       |
| application/ld+json  | json-ld           | This is the default format.|
| text/n3              | n3                |       |
| application/n-quads  | nquads            |       |
| application/trig     | trig              |       |

⚠️ **Please Note**: Browsers do not handle a number of these text-based formats, and will assume that the user wants to download the response. To force the response header `Content-Type` to have a value of `text/plain` to enable browser to display these formats, supply a `force-plain-text` GET query string parameter with a value of `true` as part of the request URL. If you are interacting with the LOD Gateway using a HTTP REST client or via code, the `force-plain-text` GET query string parameter will not be needed.

Please note all of the response formats will be UTF-8 encoded.

Assuming there was a resource `object/1` in the LOD Gateway `http://lodgateway/collection`, here are some example requests and response summaries, showing the `Content-Type` header values and the response body encodings:

```
GET http://lodgateway/collection/object/1
	--> "Content-Type: application/ld+json"
	--> (JSON-LD)

GET http://lodgateway/collection/object/1&format=nt
	--> "Content-Type: application/n-triples"
	--> (ntriples)

GET http://lodgateway/collection/object/1&format=nt&force-plain-text=true
	--> "Content-Type: text/plain"
	--> (ntriples)
```

Alternatively, here is an example of using a HTTP request `Accept` header to adjust the response format:

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

If graph functionality has been enabled for an instance of LOD Gateway, the Gateway will be able to connect with a SPARQL Update 1.1 compliant endpoint and synchronize resources ingested into the Gateway. As noted above, the Gateway will expand JSON-LD into RDF triples, and associate them with a named graph linked to the top-level `"id"` or `"@id"` value of the ingested resource. If a given resource is deleted from the LOD Gateway, its triples will be deleted from the associated graph store by deleting the named graph that contains them.

To enable graph functionality, the following environment variables must all be set appropriately (see the **Configuration** section for more information):

 * `PROCESS_RDF` must be set to `true`
 * `SPARQL_QUERY_ENDPOINT` must be set to the SPARQL query endpoint URL of the graph store
 * `SPARQL_UPDATE_ENDPOINT` must be set to the SPARQL update endpoint URL of the graph store
 * `RDF_NAMESPACE` may be set set if a different RDF namespace is required (see the paragraph below)
 
The `RDF_NAMESPACE` variable is used to determine the named graph URIs for the resources. These URIs are generated from concatenating the environment variable `BASE_URL` with `RDF_NAMESPACE` and adding the resource's `@id`/`id` to the end to form the absolute URI.

For example, if a JSON-LD document has an `@id` of `foo`, and is uploaded to an LOD Gateway with a `BASE_URL` of `https://localhost:8000` and an `RDF_NAMESPACE` of `test`, the named graph URI would be `<https://localhost:8000/test/foo>`.

If the JSON-LD is a `@graph`, the named graph part of its RDF will be overwritten by the LOD Gateway's named graph URI before updating the graph store. It will not change the JSON-LD that is stored, but it will force the triples present to be held in a single named graph.

⚠️ See the **Configuration** section below for more information on the use of, and the caveats associated with, the `RDF_NAMESPACE` environment variable.


### RDF Base Graph

If the environment variable `RDF_BASE_GRAPH` is set to an entity `"id"` (eg `_basegraph`), this document will be used as the **base graph**. The base graph is a set of triples that will be removed from any named graph RDF added to the graph store by the LOD Gateway. The base graph triples will be added to the graph store, so they will be present in the union graph. However, they will not be present in any individual named graph, besides the named graph corresponding to the base graph.

This functionality provides a toolset to deal with the issue of replicated triples between named graphs. For example, providing a human-readable `_label` to an AAT term may seem innocuous, but the same triple may be present in every named graph, and some of the LOD Gateways can have millions of named graphs. When potentially millions of replicated triples are present in the graph store, performance can be impacted significantly. By deduplicating the triples expanded from each ingested JSON-LD document, the base graph functionality helps reduce the number of triples in the graph store and thus can help restore performance. 

Changing the base graph however will **not** change the named graphs stored in the graph store retrospectively. The base graph itself will be updated in the graph store, but the application should be restarted to ensure that all web workers reload the updated triple filter set (workers will be reloaded every 1000 or so requests, but to be safe, restarting manually is recommended). After updating the base graph, to update the graph store, it will be necessary to run a `_refresh` command against all the resources that should be updated in the graph store.

 * JSON-LD documents will be unaffected by the presence of an `RDF_BASE_GRAPH`. The JSON-LD documents are stored as they are submitted.
 * SPARQL graph UNION queries should be unaffected by the presence of an `RDF_BASE_GRAPH`.
 * Queries against specific named graphs will be affected, as the individual named graphs would not contain the triples included in the base graph. However, querying individual named graphs specifically is not a current use case of the LOD Gateway.

## Default Base Graph

Any triples that are recorded in the JSON-LD will be used as the set of triples to filter from other documents. The named graph part of any quads will be discarded and replaced by the URI of the base graph in the same way that that part would be for any other uploaded document.

A default empty base graph will be added if one does not already exist, and the filter set of its triples will be loaded from this resource when the LOD Gateway instance starts up. Changing the base graph is done in the same way as uploading any other document to the LOD Gateway. It only needs to be a parsable JSON-LD document, and have the base graph relative ID.

Using a [named graph](https://www.w3.org/TR/json-ld11/#named-graphs]) in JSON-LD with `@graph` is a useful container for triples that may or may not relate to one another.

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

Here, the `@graph` container holds two unrelated triples which will be used for the filter, and a context can be used to make the document easier to read as normal:

```
<urn:test1> <rdfs:label> "nothanks" .
<urn:test2> <rdfs:label> "nothanksagain" .
```

## Versioning

If the `KEEP_LAST_VERSION` environment variable is present and set to `True`, the versioning functionality is enabled and a subset of the [Memento](http://mementoweb.org/guide/rfc/#RFC6690) specification will be provided by the LOD Gateway:

- A version of a resource will be created whenever a resource is updated with new data.
- The `Memento-Datetime` header will be included in all `GET` and `HEAD` requests for resources.
- Memento Timemaps are available for all resources, and are linked to in the `Link` header for all resource requests as specified.
  - The Timemap URIs are predictable from the resource URI. For example, `http://host/namespace/{entity-uri}` provides a timemap at `http://host/namespace/-tm-/{entity-uri}`.
- Past versions of resources are linked from the timemap, which is available in either `application/json` or `application/linked-format`. The `Accept` header of the request will be used for this content negotiation.
- The past versions are only available to authenticated clients. They include HTTP `Link` headers to the current version of the resource ('original'), and the timemap.
- The `KEEP_VERSIONS_AFTER_DELETION` affects deletion behavior. If unset, or set to `"False"`, all old versions will be deleted when the current resource is deleted. If this is set to `"True"`, all versions will be retained even if the resource is deleted, and the history will be maintained if data for the resource is uploaded again.
- While not required in the Momento specifications, the ordering of the resource and version links in the timemap will be in reverse chronological order, from newest to oldest. The first link will be the timemap, then the link to the original, and then the versions. This ordering is present in both the JSON and the `application/link-format` versions of the timemap.

Example HTTP Headers for a resource:

`GET /research/collections/place/c0380b6c-931f-11ea-9d86-068d38c13b76`

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

Example Timemap:

`GET /research/collections/-tm-/place/c0380b6c-931f-11ea-9d86-068d38c13b76`
`Accept: application/link-format`

```
<http://localhost:5100/research/collections/-tm-/place/c0380b6c-931f-11ea-9d86-068d38c13b76>;rel="self";until="2022-03-10T16:45:07";from="2022-03-10T01:12:01+0000",
<http://localhost:5100/research/collections/place/c0380b6c-931f-11ea-9d86-068d38c13b76>;rel="original",
<http://localhost:5100/research/collections/-VERSION-/ea6871b2-a81a-44d8-851a-71df92ac1002>;datetime="2022-03-10T16:42:15+0000";rel="first memento",
<http://localhost:5100/research/collections/-VERSION-/0b068854-5486-4f6c-b559-6d1b6945e247>;datetime="2022-03-10T16:41:24+0000";rel="memento",
<http://localhost:5100/research/collections/-VERSION-/9703f9b7-2116-498f-8796-12555eacaec9>;datetime="2022-03-10T16:41:22+0000";rel="memento",
<http://localhost:5100/research/collections/-VERSION-/8c4af569-5d9c-4a36-bf83-7be7f34a38e7>;datetime="2022-03-10T01:12:01+0000";rel="last memento",
```

In JSON:

`GET /research/collections/-tm-/place/c0380b6c-931f-11ea-9d86-068d38c13b76`
`Accept: application/json`

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

Versioned resources will include an `ETag` header with a SHA-256 checksum in `GET` and `HEAD` request responses. The ETag complies with [RFC7232](https://datatracker.ietf.org/doc/html/rfc7232) in how the ETag is supplied and interacted with. The checksum value will be enclosed with double-quotes `"`, and if the resource is supplied with either gzip or deflate compression, the ETag will have `:gzip` or `:deflate` appended to the checksum as the specification requires.

The `If-Match` header is not currently supported.

The `If-None-Match` header _is_ supported for `GET` or `HEAD` requests. If a checksum is supplied, it will be checked against the requested resource if the resource exists. The checksum MUST be exact and MUST NOT include any `:gzip/:deflate` suffix.

- If the checksums match, the Gateway will respond with an HTTP response status of `304` and an empty response body.
- If the checksums do not match (the resource is different compared to the local version), a normal HTTP `200 OK` response is returned.

As noted, the checksum type is SHA-256. Sample code to create a checksum is as follows:

```
import hashlib, json

def checksum_json(json_obj):
    """This helper method expects a JSON-serializable data structure as its single argument"""

    checksum = hashlib.sha256()

    # Dump the object as JSON, with the `sort_keys` flag set to `True` to ensure repeatability
    checksum.update(json.dumps(json_obj, sort_keys=True).encode("utf-8"))

    return checksum.hexdigest()
```

## Configuration

The configuration for the LOD Gateway is managed through environment variables. In a development environment (usually running on a local development computer), these variables are set through the `.env` file. In staging and production environments, these values will usually be managed and maintained in a secrets management system such as [HashiCorp](http://hashicorp.com)'s [Vault](https://www.vaultproject.io) or another integration that supplies the relevant environment variables to the Docker runtime.

The list of supported environment variables, a description of their purpose, accepted values, and where applicable, default values, are included below for reference. Please note that the example and default values may be quoted below for readability and clarity, but when specifying the values in an `.env` file or in a secrets store, the values should be entered without quotes, as `.env` files and secrets stores tend to retrieve stored values verbatim and will generally include the quotes in the returned value, which will prevent the values from being interpreted correctly by the Gateway.

```
LOD_AS_DESC ................... This variable provides a short textual description of the deployed
                                LOD Gateway and is used within the Activity Stream (AS) response
                                and the Gateway's web interface.

AUTHORIZATION_TOKEN ........... This variable defines the authorization token required for accessing
                                privileged functionality of the LOD Gateway, including ingesting
                                records, accessing earlier versions of records (if authentication is
                                required for accessing earlier versions), and other API calls
                                requiring authentication. To access privileged API functionality,
                                the HTTP request MUST include an `Authorization` header with a value
                                formatted as "Bearer {token}" where {token} is the value set for the
                                AUTHORIZATION_TOKEN environment variable. LOD Gateway functionality
                                requiring authentication is marked with a key 🗝️ symbol above.

VERSIONING_AUTHENTICATION ..... If set to "True", authentication will be required for accessing
                                earlier versions of resources. Set to "False" to allow earlier
                                versions to be retrieved without authentication. Defaults to "True".

DATABASE ...................... This should be the full URL to the database, for example:
                                "postgresql://{username}:{password}@{server}/{database}"

                                If you wish to use a temporary in-memory database for testing that
                                will just hold the data while the Gateway instance is running, but
                                will lose the data once the Gateway is shutdown, a local SQLite
                                database may be used. To use a temporary in-memory SQLite database,
                                the DATABASE variable should have a value of "sqlite:////app/app.db".

BASE_URL ...................... This should be the base URL of the application and for RDF URIs.
                                For example, "https://data.getty.edu".

APPLICATION_NAMESPACE ......... This should be the 'vanity' portion of the URL for example,
                                "museum/collection".

RDF_NAMESPACE ................. This variable is optional and should only be set if the namespace
                                in the RDF data should differ from the namespace value set in the
                                APPLICATION_NAMESPACE variable and if there is a specific need to
                                prefix the relative URLs in the JSON-LD documents differently than
                                the triples in the graph store, such as for testing purposes or for
                                specially staged loads. In such cases, these development or special
                                staging instances of the LOD Gateway must share the same base URL as
                                their corresponding production or staging instance, that is, they
                                should be hosted under the same domain name. If no RDF_NAMESPACE
                                variable is provided, the LOD Gateway defaults to using the
                                APPLICATION_NAMESPACE for data loaded into the graph store.

PROCESS_RDF ................... The value must be "True" to enable processing of JSON-LD into
                                RDF triples on ingest. If enabled, you MUST set two other
                                variables, SPARQL_QUERY_ENDPOINT and SPARQL_UPDATE_ENDPOINT, to the
                                SPARQL endpoints (query and update) of the associated graph store.

                                When PROCESS_RDF is set to "False", the LOD Gateway will act as a
                                simple JSON document store with no RDF or graph functionality.

SPARQL_QUERY_ENDPOINT ......... When graph functionality has been enabled for an LOD Gateway instance
                                via the PROCESS_RDF variable (see above), the SPARQL_QUERY_ENDPOINT
                                variable MUST also be set to the query endpoint of the associated
                                graph store.

                                The graph store must be compliant with SPARQL Update 1.1 in order
                                to be compatible with LOD Gateway. Examples of compatible graph
                                stores are Fuseki, GraphDB, Amazon Neptune, and many others.

SPARQL_UPDATE_ENDPOINT ........ When graph functionality has been enabled for an LOD Gateway instance
                                via the PROCESS_RDF variable (see above), the SPARQL_UPDATE_ENDPOINT
                                variable MUST also be set to the update endpoint of the associated
                                graph store.

                                The graph store must be compliant with SPARQL Update 1.1 in order
                                to be compatible with LOD Gateway. Examples of compatible graph
                                stores are Fuseki, GraphDB, Amazon Neptune, and many others.

USE_PYLD_REFORMAT ............. This variable controls whether PyLD or RDFLib is used to expand
                                and reformat JSON-LD into triples. If set to "True" then PyLD will
                                be used to perform graph expansion and reformatting operations,
                                otherwise RDFLib will be used instead. Defaults to "True".

RDF_BASE_GRAPH ................ Requires PROCESS_RDF to be set to "True" to have any effect. The
                                value should be the entity id of a resource that will be used as
                                the 'base graph' for the LOD Gateway.

                                Any triples in the base graph will be added to the graph store, but
                                these triples will be removed from any other ingested RDF resources
                                before they are added to the graph store.

RDF_CONTEXT_CACHE ............  A JSON-encoded value that holds an @context document to preload into the
                                PyLD or RDFLib document loader. Preloading the @context document speeds
                                up graph expansion and reformatting operations as the Gateway does not
                                need to first retrieve the @context document from the source server,
                                which is usually externally hosted.

                                If defined, the value for RDF_CONTEXT_CACHE should be in the form:
                                {"url": [context object], ...} where each [context object] is
                                structured as follows:

                                {
                                    "document": [context document],
                                    "expires": [None or datetime],
                                    "contextUrl": None,
                                    "documentUrl": None
                                }

                                The full value would then look something like the following before
                                being serialized into JSON:

                                contexts = {
                                    "https://linked.art/ns/v1/linked-art.json": {
                                        "expires": null,
                                        "contextUrl": null,
                                        "documentUrl": null,
                                        "document": {
                                            "@context": {
                                                ...
                                            }
                                        }
                                    }
                                }

                                This value MUST be serialized into a compact JSON string without unquoted
                                line breaks and with any quotes or other special characters being escaped
                                before the string value is assigned to the RDF_CONTEXT_CACHE environment
                                variable.

                                It could be serialized to JSON using code similar to the following:

                                print(json.dumps(contexts))

                                The serialized value would then look something like the below (shortened
                                for brevity):

                                "{\"https://linked.art/ns/v1/linked-art.json\": {\"document\": ... }}"

                                You can add as many @context documents into the RDF_CONTEXT_CACHE as you
                                wish to the JSON structure, ensuring that each @context document is keyed
                                on its absolute URI, such as "https://linked.art/ns/v1/linked-art.json".

RDF_CONTEXT_CACHE_EXPIRES ..... This variable controls how long a RDF context document is held in
                                the RDF context cache. Defaults to 30 seconds.

FLASK_GZIP_COMPRESSION ........ The variable must be set to "True" to enable gzip compression.
                                Defaults to "False".

PREFIX_RECORD_IDS ............. Configure the prefixing of record "id" values: the default behavior
                                is for all "id" values in a record to be discovered recursively and
                                be prefixed if necessary, if they are not to already a HTTP(S) URL
                                ("http(s)://...").

                                The default behavior will take place if PREFIX_RECORD_IDS is absent
                                from the application's environment, or if defined and configured
                                explicitly as PREFIX_RECORD_IDS=RECURSIVE.

                                The other available prefixing behaviors are to prefix only the
                                top-level "id" of the record, which may be achieved by setting
                                PREFIX_RECORD_IDS=TOP, or to disable all prefixing of record
                                "id" values by setting PREFIX_RECORD_IDS=NONE.

KEEP_LAST_VERSION ............. Set this to "True" to enable the retention of previous versions
                                of a record when it is updated. See 'Versioning' for more details.

KEEP_VERSIONS_AFTER_DELETION .. Set this to "True" to retain all versions even after deletion.
                                Trying to retrieve the resource will return a HTTP 404 error, and
                                the Activity Stream will show the item as deleted, but the HTTP
                                headers will still link to the Memento Timemap for the resource,
                                where all previous versions will be available.

LOCAL_THESAURUS_URL ........... This entry is required if APPLICATION_NAMESPACE=local/thesaurus.
                                It is the URL to the CSV file containing Local Thesaurus data that
                                will be loaded into the LOD Gateway on startup. The URL must be
                                accessible to the LOD Gateway instance's server (firewall rules must
                                allow the URL to be requested) and the LOD Gateway's DATABASE
                                variable must be set to a temporary SQLite database by setting the
                                DATABASE variable to "sqlite:////app/app.db".

SUBADDRESSING ................. To enable sub-addressing functionality, set this variable to "True",
                                or set it to "False" (the default) otherwise.

SUBADDRESSING_MIN_PARTS ....... This variable defines the smallest number of path components to
                                consider when attempting to resolve a sub-addressed path to a parent
                                entity (defaults to 1).

SUBADDRESSING_MAX_PARTS ....... This variable defines the largest number of path components to
                                consider when attempting to resolve a sub-addressed path to a parent
                                entity (defaults to 4).

LINK_BANK ..................... This field contains JSON which provides links for the 'Documentation'
                                section of the Dashboard. There can be any arbitrary number of groups
                                and links in a group. Below is an example JSON value holding a set of
                                sample links for illustration of how to structure this value:

                                {
                                  "groups": [
                                    {
                                      "name": "Some random Group",
                                      "links": [
                                        { "name": "random link 1", "url": "https://google.com" },
                                        { "name": "test link 2", "url": "https://getty.edu" },
                                        { "name": "another link 3", "url": "https://ucla.edu" },
                                        { "name": "one more link 4", "url": "https://yahoo.com" }
                                      ]
                                    },
                                    {
                                      "name": "Another Test Group",
                                      "links": [
                                        { "name": "random link 1", "url": "https://google.com" },
                                        { "name": "test link 2", "url": "https://getty.edu" },
                                        { "name": "another link 3", "url": "https://ucla.edu" },
                                        { "name": "one more link 4", "url": "https://yahoo.com" }
                                      ]
                                    },
                                    {
                                      "name": "Some random Group",
                                      "links": [
                                        { "name": "random link 1", "url": "https://google.com" },
                                        { "name": "test link 2", "url": "https://getty.edu" },
                                        { "name": "another link 3", "url": "https://ucla.edu" },
                                        { "name": "one more link 4", "url": "https://yahoo.com" }
                                      ]
                                    }
                                  ]
                                }

BROWSE_PAGE_SIZE .............. This variable sets the limit on number of records returned for a
                                glob browse request. Defaults to 200 items per page. If set, the
                                value must be set as an integer value.

LINK_HEADER_PREV_VERSION ...... This variable sets whether the `Link` response header will include a
                                reference to the previous version of the current document or not (if
                                a previous version is recorded in the Gateway). Set to "True" to
                                enable, "False" otherwise.
```


## Technical Architecture

The LOD Gateway project is built upon the following primary software components:

- [Python](https://www.python.org) version 3.10+
- [Flask](http://flask.pocoo.org)
- [SQLAlchemy](https://www.sqlalchemy.org)
- [Alembic](https://alembic.sqlalchemy.org/en/latest/)
- [PyLD](https://github.com/digitalbazaar/pyld)
- [RDFLib](https://github.com/RDFLib/rdflib)
- [Gunicorn](https://pypi.org/project/gunicorn/)

The LOD Gateway's database schema is managed via the [Alembic](https://alembic.sqlalchemy.org/en/latest/) database migration tool for [SQLAlchemy](https://www.sqlalchemy.org), which is used as the relational database interface library within LOD Gateway.


## Testing the Application

To run the Python unit tests, the following steps can be followed. In testing environments, the `.env.example` file is used directly. While the application is running, the following commands:

```bash
docker compose run --rm \
    -e APPLICATION_NAMESPACE="ns" \
    -e DATABASE=sqlite:// \
    -e AUTHORIZATION_TOKEN=AuthToken \
    web pytest
```

will run the tests, and

```bash
docker compose run --rm \
    -e APPLICATION_NAMESPACE="ns" \
    -e DATABASE=sqlite:// \
    -e AUTHORIZATION_TOKEN=AuthToken \
    web ptw
```

will run `pywatch`, which will watch for file changes and re-run the tests automatically.

Using Microsoft's VS Code editor, it is possible to develop inside the container with full debugging and _IntelliSense™_ capabilities. Port `5001` is opened for remote debugging of the Flask application. For details see: https://code.visualstudio.com/docs/remote/containers


## License & Copyright Information

Copyright © The J. Paul Getty Trust 2019 – 2023.

The Getty name, logos, and trademarks are owned by the J. Paul Getty Trust, and are subject to [the J. Paul Getty Trust Trademark Policy for Open Source Projects](https://www.getty.edu/legal/trademarks/opensource.html).
