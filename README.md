# LOD Gateway

This repository contains the code used to convert various Getty systems of record into their [Linked.art](http://www.linked.art) representations.

**Components**


**Setup Instructions**

_(This assumes that you have [Docker](https://www.docker.com/products/docker-desktop) installed.)_

The LOD Gateway is comprised of two primary services: the `transformer` and the `web-service`; for development purposes, a `postgres` service is also included.

    git clone https://github.com/thegetty/lod-gateway
    cd lod-gateway
    cp .env.example .env
    # Update the following <REDACTED> values in the .env file from Vault:
    #    DOR_API_USER
    #    DOR_API_KEY
    docker-compose build
    docker-compose up

To shut the application down:

	$ docker-compose down

**Testing the application**

_Run the python unit tests_

While the application is running,

```bash
docker-compose exec -w /app web pytest
```
will run the tests, and

```bash
docker-compose exec -w /app web ptw
```

will run `pywatch`, which will watch for file changes and re-run the tests automatically.


**Deployment Options**

For deployment, be sure to update the following ENV variables from their default values:

```
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=

LOD_DEFAULT_URL_NAMESPACE=

DOR_API_USER=
DOR_API_KEY=

VAULT_ADDR=
VAULT_ENV=
VAULT_APP_NAME=
VAULT_TOKEN=
```


**Configuration**

Configuration is managed through environment variables.  In development, these are set through the `.env` file, and in Staging and Production these are managed in Vault.

ENV Variables:

* `LOD_DEFAULT_URL_NAMESPACE`: the default namespace for URLs routes, if one is not provided.

**Technical Architecture**

The LOD Gateway project consists of the following primary software components:

- [Python](https://www.python.org) version 3.7+
- [CROM](https://github.com/thegetty/crom)
- [Flask](http://flask.pocoo.org)
- [Psycopg2](http://initd.org/psycopg/)

The proposed process of operation will involve supporting two modes of operation, the initial (bulk) mode will allow the process to iteratively consume all object records from the DOR one-by-one and generate the relevant JSON-LD representation of each and any relevant related records. Once this initial pass has been completed, the system will be able to regenerate the JSON-LD representation of the records which have changed in the DOR via a change-notification mechanism. The list of changed records will be obtained via an Activity Streams API provided by the DOR (to be built in aid of this project and other future projects) which can be consumed by the transformation process on a periodic basis (timing to be determined, but at least once per day) and then any changed or new records will be obtained, and regenerated as needed. The transformation process will also remove any records from the LOD Gateway data set if any have been deleted or rescinded in TMS, and thus in the DOR through its nightly synchronization with TMS.

The source code for the primary services may be found nested within the top-level `source` directory within this repository, and the `postgres` service configuration may be found within the top-level `services` directory. Each service has its own `Dockerfile` and these are tied together for development via the project's `docker-compose.yml` file. Configuration settings for the application are defined within an `.env` file, which is read by the `docker-compose` command automatically into the build and runtime environment via the `docker-compose.yml` file. More information on configuring the application may be found below in the **Configuration** section.

While the `Dockerfile` for each of the application's services copy in the necessary source code assets, as an affordance for development, the project's `docker-compose.yml` file mounts the project's source code over the copied source code assets within each resulting Docker container. This means that when the application is run via `docker-compose`, changes made to project source code in the project repository are immediately reflected within the relevant service container. This allows iterative changes to be made to the project code efficiently without having to continually rebuild the Docker containers and relaunch the application, thus saving a great deal of time.

The LOD Gateway currently supports two styles of deployment: being deployed as a single (optionally clustered) instance with a single (optionally clustered) data store, that hosts multiple datasets, or as many independent instances with their own endpoints and data stores to hold each data set independently. When the system is deployed as a single instance, the concept of a namespace becomes very useful as it allows the system to handle and segment the various data sets it may contain. The namespace becomes part of the unique record URL for each record in the system, along with the record's entity type name, and unique identifier. When multiple independent instances of the LOD Gateway are deployed, the namespace concept remains valuable as a way to uniquely associate any given LOD record URL with a particular LOD Gateway instance, where the namespaces present in the endpoint URLs can be used to help route requests to the relevant LOD Gateway instance. The **Configuration** section below contains more information on the various configuration options and how they are used by the deployments.

**License and Copyright Information**

Copyright © The J. Paul Getty Trust 2019. All rights reserved.
