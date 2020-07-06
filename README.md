# LOD Gateway

This repository contains the code used to convert various Getty systems of record into their [Linked.art](http://www.linked.art) representations.

**Components**

The LOD Gateway contains one production container: `web-service`; for development purposes, a `postgres` service is also included.

**Setup Instructions**

_(This assumes that you have [Docker](https://www.docker.com/products/docker-desktop) installed.)_

    git clone https://github.com/thegetty/lod-gateway
    cd lod-gateway
    cp .env.example .env
    docker-compose build
    docker-compose up

To shut the application down:

    docker-compose down

When first creating an application instance, the application database schema must be manually created through the Alembic database migration tool for SQLAlchemy. With the proper database connection defined in the .env file, exec into a locally running `web-service` container and execute:

    flask db upgrade

or, from the host command line:

    docker exec `docker ps -q -f publish=5100` flask db upgrade

**Testing the application**

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


**Deployment Options**

Configuration is managed through environment variables.  In development, these are set through the `.env` file, and in Staging and Production these are managed in Vault.  In testing environments, the .env.example file is used directly.

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
```

Using VS Code, it is possible to develop inside the container with full debugging and intellisence capabilities. Port 5001 is opened for remote debugging of the Flask app. For details see: https://code.visualstudio.com/docs/remote/containers


**Technical Architecture**

The LOD Gateway project consists of the following primary software components:

- [Python](https://www.python.org) version 3.7+
- [Flask](http://flask.pocoo.org)
- [SQLAlchemy](https://www.sqlalchemy.org)


**License and Copyright Information**

Copyright © The J. Paul Getty Trust 2019-2020. All rights reserved.
