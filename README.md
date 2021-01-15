# LOD Gateway

This repository contains the code used to convert various Getty systems of record into their [Linked.art](http://www.linked.art) representations.

## Components

The LOD Gateway contains one production container: `web-service`; for development purposes, a containerized `postgres` service is also included.

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

## Testing the application

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

Configuration is managed through environment variables.  In development, these are set through the `.env` file, and in Staging and Production these are managed in Vault.  In testing environments, the `.env.example` file is used directly.

```
AUTHORIZATION_TOKEN=        # Token required for 'Ingest' functionality

DATABASE=                   # This should be the full URL to the database
                            # for example, postgresql://mart:mart@postgres/mart

LOD_BASE_URL=               # This should be the base URL of the application
                            # for example, https://data.getty.edu

APPLICATION_NAMESPACE=      # This should be the 'vanity' portion of the URL
                            # for example, "museum/collection"

APP_NAMESPACE_NEPTUNE=      # This variable should always have the same value as
                            # APPLICATION_NAMESPACE unless there is a specific need
                            # to prefix the relative URLs in the JSON-LD documents
                            # differently for Neptune, such as for testing or for
                            # specially staged loads. In such cases, these development
                            # or special stagining instances of the LOD Gateway must
                            # share the same base URL as their corresponding production
                            # or staging instance, that is, they should be hosted under
                            # the same domain name.

PROCESS_NEPTUNE=            # The value must be "True" if Neptune processing is required

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

KEEP_LAST_VERSION=.         # Set this to True to enable the retention of a single previous
                            # version of a record when it is updated. See 'Versioning' for
                            # more details.
```

Using VS Code, it is possible to develop inside the container with full debugging and intellisence capabilities. Port 5001 is opened for remote debugging of the Flask app. For details see: https://code.visualstudio.com/docs/remote/containers

## Logging and Access logs

The logging configuration creates two StreamHandlers - one that will output all python logger messages to stdout, and only logging.CRITICAL and logging.ERROR to stderr. This is desired to make it easier to track fatal errors once deployed. This configuration is written to the root logger, and is inherited by logger objects created subsequently. The log level is set using the `DEBUG_LEVEL` environment variable is should be set to a standard python log level (`DEBUG, INFO, WARNING, ERROR, CRITICAL`). The log levels in order of severity, and runs from left to right from least to most severe. What this means is that if the level is set to `DEBUG`, all messages marked `DEBUG` and more severe (all down to `CRITICAL` level) are logged. Set the level to `ERROR`, then only `ERROR` and more severe (only `CRITICAL` by default) are logged.

The uWSGI hosts the python application as a wsgi application. It pipes the stdout and stderr messages as intended by the python application. It also generates its own log messages relating to hosting the web service, both access request logs as well as health and service messages. The base configuration is in `source/web-service/uwsgi.ini`. Many other deployment-specific options can still be set using environment variables (such as UWSGI_THREADS, UWSGI_PROCESSES) at runtime, but the .ini file sets up the baseline logging set up.

### Log routing:

**stdout**

 - python logger output? ALL `DEBUG, INFO, WARNING, ERROR, CRITICAL`.
 - uWSGI messages? All messages.

**stderr**

 - python logger output? `ERROR` and `CRITICAL` only.
 - uWSGI messages? Only HTTP 50X messages (via a log-route match in uwsgi.ini)
 
## Versioning

If the KEEP_LAST_VERSION environment variable is present and set to 'True', it turns on functionality to keep a single previous copy of an upload, and to connect it to the new version. This is done by copying the data to a new record with an arbitrary new entity_id, and adding a reference to this in the Record.previous_version field of the newer record. The JSON data is unchanged in the previous verison, and will retain whatever value the record had in the 'id' field.

Why use 'entity_id'?
This enables the previous version to be accessible through the API in normal ways without impacting currently established functionality.

When enabled, a record response will include two new headers X-Previous-Version and X-Is-Old-Version.

If there is a previous version of the record, the X-Previous-Version will contain the entity_id for it, and it will be accessible through 'http://host:port/{NAMESPACE}/{entity_id}' as usual.

When accessing an old version, the X-Is-Old-Version header will be True.

When a new version requested to be ingested, any previous version is deleted and replaced with the current version.
The uploaded version will become the current version.

Deleting a record will also delete any previous version stored.

Actions on previous versions will not be logged to the activity stream, which will only contain actions performed on
current versions.

Example response HTTP headers for a record that has a previous version:

    Access-Control-Allow-Origin *
    Content-Length  120
    Content-Type    application/json
    Date    Tue, 20 Oct 2020 19:38:56 GMT
    ETag    f527e7baebd62fe983a2f1add8c7931efbf38e485dcceea1766191192bf8ddc4
    Last-Modified   2020-10-20T19:38:53
    Server  LOD Gateway/0.2
    X-Is-Old-Version    None
    X-Previous-Version  05358b54-4781-4d3e-bd08-7e9d06321c23

In this case, the previous version can be retrieved from http://{HOST}:{PORT}/{NAMESPACE}/05358b54-4781-4d3e-bd08-7e9d06321c23. It will include the header X-Is-Old-Version set to True.

## Technical Architecture

The LOD Gateway project consists of the following primary software components:

- [Python](https://www.python.org) version 3.7+
- [Flask](http://flask.pocoo.org)
- [SQLAlchemy](https://www.sqlalchemy.org)


## License and Copyright Information

Copyright © The J. Paul Getty Trust 2019-2020. All rights reserved.
