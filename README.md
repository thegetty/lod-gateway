# LOD Gateway
This repository contains the code used to convert various Getty systems of record into their [Linked.art](http://www.linked.art) representations.

Initially the repository contains test code to try out [CROM](http://github.com/thegetty/crom) for building out the [Linked.art](http://www.linked.art) JSON-LD representation of Van Gogh's [_Irises_](http://www.getty.edu/art/collection/objects/826/) (1899) – the sample record chosen as the starting point of the conversion process due to its depth and breadth of cataloguing as well as its popular status within the colleciton.

The project will eventually allow the conversion of the entirety of the Museum's publicly cleared collections data in support of the Collection Online retrofit project and other future presentaions of the Museum's Collection information based on LOD principles and practices.

**Components**

The LOD Gateway project consists of the following primary software components:

- [Python](https://www.python.org) version 3.7+
- [CROM](https://github.com/thegetty/crom)
- [Flask](http://flask.pocoo.org)
- [Psycopg2](http://initd.org/psycopg/)

**Setup Instructions**

The LOD Gateway project application is containerised using Docker, and comprises of two primary services: the `transformer` and the `web-service`, and for development purposes, a third `postgres` service is bundled with the application to allow for local development as well as to support continuous integration testing. The source code for the primary services may be found nested within the top-level `source` directory within this repository, and the `postgres` service configuration may be found within the top-level `services` directory. Each service has its own `Dockerfile` and these are tied together for development via the project's `docker-compose.yml` file. Configuration settings for the application are defined within an `.env` file, which is read by the `docker-compose` command automatically into the build and runtime environment via the `docker-compose.yml` file. More information on configuring the application may be found below in the **Configuration** section.

The installation, build and startup instructions for development are as follows:

1. Ensure that [Docker Desktop](https://www.docker.com) is installed on your system; follow the instructions available at: https://www.docker.com/products/docker-desktop.
2. Clone the project repository from GitHub: `git clone https://github.com/thegetty/museum-collections-data-to-linked-art museum-art`
3. Switch to the local project repository directory: `cd museum-art`
4. To build or rebuild the container, run: `docker-compose build`
5. To start the application, run: `docker-compose up`

While the `Dockerfile` for each of the application's services copy in the necessary source code assets, as an affordance for development, the project's `docker-compose.yml` file mounts the project's source code over the copied source code assets within each resulting Docker container. This means that when the application is run via `docker-compose`, changes made to project source code in the project repository are immediately reflected within the relevant service container. This allows iterative changes to be made to the project code efficiently without having to continually rebuild the Docker containers and relaunch the application, thus saving a great deal of time.

As each service has its own default `ENTRYPOINT` / `CMD` configured, when working with the project in a development capacity, it is useful to interact with each container via the shell. This can be achieved using the `exec` subcommand of `docker-compose` as follows, with `bash` being the preferred shell for this project:

	$ docker-compose exec <service> bash
	
One should replace `<service>` in the command above with the relevant name of one of the application's available services, which are currently comprised of the following:
	
- `postgres`
- `transformer`
- `web-service`

Overall the setup process would look something like this:

	$ git clone https://github.com/thegetty/museum-collections-data-to-linked-art museum-art
	$ cd museum-art
	$ docker-compose build
	$ docker-compose up

To shut the application down at any time, from within the root of the project's source code repository run the following:

	$ docker-compose down
	
This may take several seconds to complete, to allow the safe shutdown of the application's bundled PostgreSQL instance.

**Local Deployment Instructions**

This section is currently does not apply to this repository. It will be updated as the project matures.

**Additional Commands**

This section is currently does not apply to this repository. It will be updated as the project matures.

**Technical Architecture**

The proposed process of operation will involve supporting two modes of operation, the initial (bulk) mode will allow the process to iteratively consume all object records from the DOR one-by-one and generate the relevant JSON-LD representation of each and any relevant related records. Once this initial pass has been completed, the system will be able to regenerate the JSON-LD representation of the records which have changed in the DOR via a change-notification mechanism. The list of changed records will be obtained via an Activity Streams API provided by the DOR (to be built in aid of this project and other future projects) which can be consumed by the transformation process on a periodic basis (timing to be determined, but at least once per day) and then any changed or new records will be obtained, and regenerated as needed. The transformation process will also remove any records from the LOD Gateway data set if any have been deleted or rescinded in TMS, and thus in the DOR through its nightly synchronization with TMS.

**License and Copyright Information**

Copyright © The J. Paul Getty Trust 2019. All rights reserved.
