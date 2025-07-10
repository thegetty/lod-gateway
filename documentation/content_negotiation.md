# Content Negotiation

## Overview

The LOD Gateway when configured to support RDF Processing provides support for both standard HTTP Content Negotiation of mimetype as well as data-specific support for [Content Negotiation by Profile from the W3C](https://www.w3.org/TR/dx-prof-onneg/) (aka CNBP).

The content negotiation supports requests using the HTTP Headers `Accept`, and `Accept-Profile`, as well as URL Query String Arguments (QSA) `_profile`, `_mediatype` (or `format`). The `Accept` header is handled as standard. The `Accept-Profile` header are handled as specified in [this section](https://www.w3.org/TR/dx-prof-conneg/#getresourcebyprofile) and use of the QSA [is outlined here](https://www.w3.org/TR/dx-prof-conneg/#qsa).

## What CNBP aspects are supported

- HEAD/GET requests on resources return Link headers that specify the alternate profiles that the resource can be retrieved as.
- QSA pattern support for resource retrieval under a given profile (eg `http://example.org/a&_profile=...`)
- Accept-Profile header support for resource retrieval under a given profile (eg `Accept-Profile: <http://my.profile.spec/1>`)
- Accept header and QSA `_mediatype` and `format` parameters can be used to render the resource in alternate RDF formats (eg `http://example.org/a&format=nt` or `Accept: application/n-triples`).
- The list of both the acceptable profiles and RDF formats can be specified in the same request, and the best combination will be used to form the response.

## What CNBP aspects LOD Gateway does NOT Support
The LOD Gateway does NOT have a full implementation of every suggested access pattern CNBP W3C specification, and supports only the QSA patterns, and the Accept-Profile header for accessing a resource rendered under a selected profile.
- Getting a profiled resource by using a profile key:value statement within an Accept header. For example `Accept: application/ld+json;charset=UTF-8;profile=<http....>`. This has been omitted from the first release of this functionality for simplicity but may be added in at a later date. This would be treated as lower priority than Accept-Profile, and the profile would inherit the q-values for the Accept mimetype it applies to.
- Getting a profiled resource by using Link headers in the request. The Link header format is tricky to parse, and to form correctly, and the QSA pattern or the use of Accept-Profile are a much more robust path, and much easy to test and use especially by editing URLs in a browser. If compatibility with this request pattern is required, it will be added at a later date.

## Response flow

The following diagram outlines the broad decisions and priorities when determining what is preferred and acceptable based on the request received. 

```mermaid
graph TD
    A[Record exists] --> B{Check eTag for If-None-Match?}
    B -- Yes --> M[Return empty HTTP 304] --> K
    B -- No --> C
    C[Parse headers and parameters<br>Determine content negotiation and/or profile info<br>Mimetype priority: _mediatype or format > Accept header<br>Profile priority: _profile > Accept-Profile > Profile] --> D{Relative ID requested}
    D -- Yes --> N[Return raw JSON-LD, unprefixed w/ eTag] --> K
    D -- No --> F[Prefix all relative IDs in JSON/JSON-LD]
    F --> G{Mimetype is JSON-LD<br>and no profile?}
    G -- Yes --> H[Return prefixed JSON-LD as is w/ eTag] --> K
    G -- No --> I{Requested profiles exist?}
    I -- Yes --> J[Satisfy first supported profile with SPARQL pattern] --> Q
    Q[Reformat data into desired format, NO eTag!] --> K
    I -- No --> Q
    K[Return Response with appropriate mimetype unless plaintext is requested]
```

## RDF Format Support

The following mimetypes are supported for the `_mediatype`, `format` or Accept header. The QSA parameter and the `format` parameter also supports a number of shorthand values for certain types, and these are the short strings shown after the mimetype below:

- `application/n-triples` (`application/ntriples` also accepted), "nt11"|"nt"
- `text/turtle`, "turtle"
- `application/rdf+xml`, "xml"
- `text/n3`, "n3"
- `application/n-quads`, "nquads"
- `application/ld+json`, "json-ld"
- `application/trig`, "trig"

## Force plain text mimetype in the response

The URL parameter `plaintext` or `force-plain-text` can be used to override the stated HTTP response mimetype. This is most useful when trying to view a given RDF format in a web browser when it does not support the RDF mimetype (even though it is a plain-text based format). For example, a browser will attempt to download a response in the N-Triples mimetype, rather than attempt to display it. Adding `&plaintext=true` to the parameters will give the response a mimetype of `text/plain` allowing the browser to display it.
