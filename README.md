# Museum [Linked] ART (MART) Project
This repository contains the code used to convert the Museum's Collections Information into its [Linked.art](http://www.linked.art) representations, for the remainder of this document known as the MART project for brevity.

Initially the repository contains test code to try out [CROM](http://github.com/thegetty/crom) for building out the [Linked.art](http://www.linked.art) JSON-LD representation of Van Gogh's [_Irises_](http://www.getty.edu/art/collection/objects/826/) (1899) – the sample record chosen as the starting point of the conversion process due to its depth and breadth of cataloguing as well as its popular status within the colleciton.

The project will eventually allow the conversion of the entirety of the Museum's publicly cleared collections data in support of the Collection Online retrofit project and other future presentaions of the Museum's Collection information based on LOD principles and practices.

**Components**

The MART project consists of the following proposed software components:

- [Python](https://www.python.org) version 3.7+
- [CROM](https://github.com/thegetty/crom)
- [Flask](http://flask.pocoo.org)

**Setup Instructions**

The installation instructions currently stand as follows; these will be updated over time as the repository and its capabilites evolve.

1. Ensure that [Docker Desktop](https://www.docker.com) is installed on your system; follow the instructions available at: https://www.docker.com/products/docker-desktop.
2. Clone the project repository from GitHub: `git clone https://github.com/thegetty/museum-collections-data-to-linked-art museum-art`
3. Switch to the local project repository directory: `cd museum-art`
4. To build or rebuild the container, run: `docker build --tag museum-art-app .`
5. To start the application, run: `docker run --name museum-art -p 5000:5000 museum-art-app`
6. Repeat steps 4/5 as needed during development and testing.

Overall the setup process would look something like this:

	$ git clone https://github.com/thegetty/museum-collections-data-to-linked-art museum-art
	$ cd museum-art
	$ docker build --tag museum-art-app .
	$ docker run --name museum-art -p 5000:5000 museum-art-app

**Local Deployment Instructions**

This section is currently does not apply to this repository. It will be updated as the project matures.

**Additional Commands**

This section is currently does not apply to this repository. It will be updated as the project matures.

**Technical Architecture**

The proposed process of operation will involve supporting two modes of operation, the initial (bulk) mode will allow the process to iteratively consume all object records from the DOR one-by-one and generate the relevant JSON-LD representation of each and any relevant related records. Once this initial pass has been completed, the system will be able to regenerate the JSON-LD representation of the records which have changed in the DOR via a change-notification mechanism. The list of changed records will be obtained via an Activity Streams API provided by the DOR (to be built in aid of this project and other future projects) which can be consumed by the transformation process on a periodic basis (timing to be determined, but at least once per day) and then any changed or new records will be obtained, and regenerated as needed. The transformation process will also remove any records from the MART data set if any have been deleted or rescinded in TMS, and thus in the DOR through its nightly synchronization with TMS.

**License and Copyright Information**

© The J. Paul Getty Trust 2019. All rights reserved.
