# Linked Data Platform Backend and API
([back to ToC](/README.md))
## Overview
The [Linked Data Platform (LDP)](https://www.w3.org/TR/ldp/#ldpc) is a W3C standard that defines a set of rules for interacting with web resources using HTTP, enabling a read-write Linked Data architecture on the web. It provides a way to access, create, update, and delete RDF resources over HTTP in a standardized manner, facilitating data integration and interoperability. LDP builds upon the principles of Linked Data, using URIs as names for things, providing useful information when a URI is looked up, including links to other URIs.

One of the core concepts is the idea of a 'container' which contains zero or more Linked Data resources as a set. A container may have resources added or removed from it, and when resolving its URI, it should be possible to find out more about the container as well as list every resource it contains. A container may contain almost anything that can be referenced with a URI.

When the LDP features are enabled, the LOD Gateway is extended with container structures, and the service itself is viewed as having a single 'root' container, that everything else (resources and other containers) is part of. The API is also extended, to allow for a subset of the LDP API functionality as defined in the specification.

### Limited Support for the Full LDP Specification
The LOD Gateway and the LDP specification are based around different ideas on how to handle and store Linked Data: 
- The LOD Gateway is built around a CRUD API for JSON documents and extends that by adding optional Named Graph JSON-LD RDF capabilities, Content Negotiation, SPARQL, Activitystreams and fast bulk ingest and updating.
- LDP is a much broader specification which can involve both RDF and Non-RDF resources such as images, and specifies the concepts and API for containers. The focus is on the REST API that is required to manage these resources and containers.

The LOD Gateway implementation supports a narrower portion of the full LDP specification:

- The LOD Gateway LDP support is dependent on RDF support also being enabled (PROCESS_RDF=True)
- The LOD Gateway root path is the root in the container hierarchy.
- The Container hierarchy will mirror the URL path. eg /annotations/test/12345 will have the following container hierarchy:
    - root '/' <-member- '/annotations/' <-member- '/annotations/test/' <-member '/annotations/test/12345'
- A Container will contain either other containers, or named graphs (the JSON-LD documents). 
    - Adding binary or Non-RDF content will be not supported
- The LOD Gateway will use ldp:BasicContainers and only supports dc:title and dc:description fields for their user-editable metadata.
- Pagination using the [LDP-PAGING specification](https://www.w3.org/TR/ldp-paging/) will be the default, and the members will be listed containers-first and then the member JSON-LD resources. This will be an ordered but dynamic response, so page responses may vary after resources are deleted.
    - This is usefully different to the existing static activitystream responses, as the container listing will only contain members that are part of that container at the time of querying, and will not list deleted members.
- Containers and Named Graphs must be added to an existing container resource, or the request will fail:
    - A POST request to a container, using the Slug header to specify an optional relative identifier.
    - A PUT request to a specific path. The Slug will be inferred from the path.

NB There is an optional feature that can be enabled to make the LOD Gateway automatically create the necessary container structure if it does not exist.
