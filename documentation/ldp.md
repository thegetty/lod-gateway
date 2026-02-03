
# Linked Data Platform Backend and API
([back to ToC](/README.md))
## Overview
The [Linked Data Platform (LDP)](https://www.w3.org/TR/ldp/#ldpc) is a W3C standard that defines a set of rules for interacting with web resources using HTTP, enabling a read-write Linked Data architecture on the web. It provides a way to access, create, update, and delete RDF resources over HTTP in a standardized manner, facilitating data integration and interoperability. LDP builds upon the principles of Linked Data, using URIs as names for things, providing useful information when a URI is looked up, including links to other URIs.

One of the core concepts is the idea of a 'container' which contains zero or more Linked Data resources as a set. A container may have resources added or removed from it, and when resolving its URI, it should be possible to find out more about the container as well as list every resource it contains. A container may contain almost anything that can be referenced with a URI.

When the LDP features are enabled, the LOD Gateway is extended with container structures, and the service itself is viewed as having a single 'root' container, that everything else (resources and other containers) is part of. The API is also extended, to allow for a subset of the LDP API functionality as defined in the specification.

### Quick overview of some useful LDP Concepts

LDP introduces two major categories of resources:

- Linked Data Platform Resources (LDPRs), web resources that follow LDP interaction patterns.
- Linked Data Platform Containers (LDPCs), specialized LDPRs that act like collections or 'buckets' for managing membership.

An *RDF Source* (LDP-RS) is an LDPR whose state is represented entirely as RDF. It supports operations using standard HTTP methods (eg GET, DELETE), and the server exposes its content as an RDF graph.

A *BasicContainer* is the simplest form of an LDP container. It is an RDF Source (i.e., an LDP-RS) that also conforms to additional rules for managing linked membership.

- It uses a simple, predefined predicate (ldp:contains) to list resources they contain.
- Allow creation of new contained resources via HTTP POST.
- Provide predictable, REST-friendly behavior similar to folders or AtomPub collections.

#### How BasicContainers and RDF Resources Work Together

A BasicContainer is itself an RDF Source that describes:

- Its own metadata, (NB currently only dcterms:title and dcterms:description are supported) and
- A set of ldp:contains triples pointing to resources created within it.

When a client POSTs to a BasicContainer:

The server creates a new LDPR.
The container automatically adds a membership triple linking to that new resource.

This structure enables predictable navigation and management of collections in a RESTful, linked-data‑friendly way. It functions similarly to a blog with posts or a directory with files—except using RDF semantics and HTTP.

### Overview of Support for these LDP Concepts
The LOD Gateway and the LDP specification are based around different ideas on how to handle and store Linked Data: 
- The LOD Gateway is built around a CRUD API for JSON documents and extends that by adding optional Named Graph JSON-LD RDF capabilities, Content Negotiation, SPARQL, Activitystreams and fast bulk ingest and updating.
- LDP is a much broader specification which can involve both RDF and Non-RDF resources such as images, and specifies the concepts and API for containers. The focus is on the REST API that is required to manage these resources and containers.

The LOD Gateway implementation supports a narrower portion of the full LDP specification:

- The LOD Gateway LDP support is dependent on RDF support also being enabled (`PROCESS_RDF` set to True)
- The LOD Gateway will contain a **single** root Container `/` which *every* resource will be a child of, indirectly or directly.
- Only the ldp:BasicContainer is supported, with direct managed membership. This mirrors how LOD Gateway manages the Named Graphs uploaded to it.
- The Container hierarchy will mirror the URL path. eg /annotations/test/12345 has the following container hierarchy:
```
/ (root)
    --ldp:contains--> /annotations/
        --ldp:contains--> /annotations/test/
            --ldp:contains--> `/annotations/test/12345
```

- A Container will contain either other ldp:BasicContainer Resources, or named graphs (the JSON-LD documents that a level 2 LOD Gateway usually contains). 
    - Adding binary or Non-RDF content will be not supported at this time.
- The LOD Gateway will use ldp:BasicContainers and only supports dc:title and dc:description fields for their user-editable metadata.
- Pagination using the [LDP-PAGING specification](https://www.w3.org/TR/ldp-paging/) will be the default, and the members will be listed containers-first and then the member JSON-LD resources. This will be an ordered but dynamic response, so page responses may vary after resources are deleted. In order to make parsing the Container response more predictable, all Container responses will be paginated, regardless to how many Resources it contains.
    - This is usefully different to the existing static activitystream responses, as the container listing will only contain members that are part of that container at the time of querying, and will not list deleted members.
- Containers and Named Graphs must be added to an existing container resource, or the request will fail:
    - A POST request to an existing container, containing a JSON-LD formatted resource.
        - If a top-level id is not present, the LOD Gateway will generate and add one. While this is configured through the 'LDP_ID_GEN' environment variable, only 'uuid' is supported. Other methods can be added as required later.
        - A Slug header can be used to specify a desired (leaf) 'identifier' for the graph. For example, a POST to `/objects/my-container/` with a slug of `annotation1` will result in a URI of `/objects/my-container/annotation1`

### Two-tiered service levels - LDP_BACKEND and LDP_API
`LDP_BACKEND` can be enabled without any other LDP feature turned on. This allows an LOD Gateway with existing datasets access to the DB models required to support LDP, and the ability to generate the necessary Containers gradually in the background rather than require the whole service's dataset be updated at once. `LDP_BACKEND` must be enabled for all LDP functionality.

The setting `LDP_AUTOCREATE_CONTAINERS` when enabled is the key to this process. When both of the above settings are enabled, adding to or refreshing content in the LOD Gateway will auto-populate the LDP data that is required. In other words, the same maintenance mechanism that allows an administrator to refresh a Triplestore will generate the Container and Container member tables as well.

`LDP_API` can be enabled to support the LDP REST API. This supports Container resolution, pagination, and a Container POST endpoint to allow authenticated users to create or add resources (including other containers). It is safe to enable this from the start on any newly deployed LOD Gateway instance, but enabling it on existing instances will require the data to be refreshed before use, as described above. Otherwise, the containers will not be present or have a valid list of child resources that they manage.

### LDP POST examples

When a JSON-LD document is uploaded using the LDP POST API, the document's internal or self-referencial '@id' properties will need to be 'rebased' to match the destination URI. For example:

Example document:
```
{
"@context": {"@base": "http://other-site/profile/"}, 
  "@id": "me"
}
```
If this is POSTed to a container at `https://data.getty.edu/research/collections/people/`, the relative URIs will be repointed or rebased to its new location:
```
{
"@context": {"@base": "https://data.getty.edu/research/collections/"}, 
  "@id": "people/me"
}
```
 The document 'rebasing' and primary URI generation is a complex, but intuitive feature of the LDP POST API and is necessary to make LDP ideas work with the existing LOD Gateway conventions.

- Absolute URIs will be unaffected (eg `"@id": "https://remote/server/aat/123450"`) will not be changed.
- Explicit blank nodes will be unaffected. (eg "_:...")
- `@base` properties already in the context will be used to change the relative URIs to match the destination
- If a resource is POSTed with a `Slug` HTTP header, then, the top-level URI (and its relative children) WILL BE REPLACED by the Slug prefix.

#### Examples of rebasing
(All examples will be POSTed to `/my-container/` on `https://data.getty,edu/demo`)
##### Example 1
```
{
    "@context": "https://www.w3.org/ns/anno.jsonld",
    "type": "Annotation",
    "body": {
        "type": "TextualBody",
        "value": "I like this page!",
        "format": "text/plain",
    },
    "target": "http://www.example.com/index.html",
}
```
##### Example 1 POSTed with no Slug:
```
{
  "@context": "http://www.w3.org/ns/anno.jsonld",
  "@id": "https://data.getty,edu/demo/my-container/d4c28721-d8a8-4d5f-9f22-7ae6bc0d5ad2",
  "type": "Annotation",
  "body": {
    "type": "TextualBody",
    "value": "I like this page!",
    "format": "text/plain"
  },
  "target": "http://www.example.com/index.html"
}
```
##### Example 2
```
 {
    "@context": ["https://www.w3.org/ns/anno.jsonld", {"@base": "urn:"}],
    "type": "AnnotationCollection",
    "id": "this",
    "first": [
        {
            "id": "this/1",
            "body": {
                "id": "http://some/aat/classification",
            },
            "target": "http://www.example.com/irises.jpg",
            "agent": {
                "type": "Software",
                "name": "Unique name for the ML classification service and version",
            },
        },
        {
            "id": "this/2",
            "body": {
                "type": "TextualBody",
                "value": "A collection of flowers",
                "format": "text/plain",
            },
            "target": "http://www.example.com/irises.jpg",
        },
    ],
}
```
##### Example 2, POSTed with the Slug 'not-this'
NB Note the rebasing, and the shift from 'this' to 'not-this' URI ending, and how its children have been shifted as well, retaining their own identifier hierarchy (`this/1` -> `not-this/1`)
```
{
  "@context": "https://www.w3.org/ns/anno.jsonld",
  "type": "AnnotationCollection",
  "id": "https://data.getty.edu/demo/my-container/not-this",
  "first": [
    {
      "id": "https://data.getty.edu/demo/my-container/not-this/1",
      "body": {
        "id": "http://some/aat/classification"
      },
      "target": "http://www.example.com/irises.jpg",
      "agent": {
        "type": "Software",
        "name": "Unique name for the ML classification service and version"
      }
    },
    {
      "id": "https://data.getty,edu/demo/my-container/not-this/2",
      "body": {
        "type": "TextualBody",
        "value": "A collection of flowers",
        "format": "text/plain"
      },
      "target": "http://www.example.com/irises.jpg"
    }
  ]
}
```

##### Example 3
Complex @graph-based JSON-LD

```
{
    "@graph": [
        {"@id": "items/780"},  # Will shorten
        {"@id": "items/780/anno/456"},
        {"@id": "#frag"},  # not actually in the 'items' graph => no slug
        {"@id": "_:b1"},
        {"@id": "items/780/absolute/path"},
        {"@id": "someotherthing/annotation"},  # This will not gain the new slug
        {"@id": "http://another.host/things?id=1#part"},  # left unchanged
    ],
    "@id": "items/780",
    "@type": "https://www.w3.org/2004/03/trix/rdfg-1/Graph",
    "@context": {"name": "http://schema.org/name", "@base": "urn:"}, 
}
```

##### Example 3, POSTed with Slug 'newitems/780'
(getting the '?relativeid=true' representation of the Resource:)
```
{
  "@graph": [
    {
      "@id": "my-container/newitems/780"
    },
    {
      "@id": "my-container/newitems/780/anno/456"
    },
    {
      "@id": "my-container#frag"
    },
    {
      "@id": "_:b1"
    },
    {
      "@id": "my-container/newitems/780/absolute/path"
    },
    {
      "@id": "my-container/someotherthing/annotation"
    },
    {
      "@id": "http://another.host/things?id=1#part"
    }
  ],
  "@id": "my-container/newitems/780",
  "@type": "https://www.w3.org/2004/03/trix/rdfg-1/Graph",
  "@context": {
    "name": "http://schema.org/name",
    "@base": "http://localhost:5100/museum/collection/"
  }
}
```

**IMPORTANT**: This HTTP POST would NOT have worked if `LDP_AUTOCREATE_CONTAINERS` was not set to True. To create a resource with a slug of `newitems/780`, this implies that there must be a new container at `newitems`. With this set to True, the following container is autogenerated as part of the transaction to add the above graph:


`GET /my-container/newitems/?page=1`


```
{
  "@context": [
    {
      "ldp": "http://www.w3.org/ns/ldp#",
      "dcterm": "http://purl.org/dc/terms/",
      "@base": "http://localhost:5100/museum/collection/"
    }
  ],
  "@id": "my-container/newitems/",
  "dcterm:title": "/my-container/newitems/",
  "@type": [
    "ldp:BasicContainer",
    "ldp:Container"
  ],
  "dcterm:description": "Auto-generated container",
  "ldp:contains": [
    {
      "@id": "my-container/newitems/780",
      "dcterm:type": "https://www.w3.org/2004/03/trix/rdfg-1/Graph",
      "dcterm:available": "2026-02-03T00:26:35+0000"
    }
  ]
}
```


