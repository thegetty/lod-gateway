LOD Gateway - Changelog
=======================

v2.6.0b RDF Prefix fix
v2.6.0b - Created: 2024-09-23T17:25:48Z

## What's Changed
* RDF prefixes used in 'id' fields should not be treated as relative URIs by @benosteen in https://github.com/thegetty/lod-gateway/pull/472


**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v2.6.0...v2.6.0b
=======================================

v2.6.0 Dashboard, skip-to-datetime activitystream, and updates.
v2.6.0 - Created: 2024-09-03T17:22:26Z

## What's Changed
* bug of single record fixed by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/443
* Migrate to 'main' branch as default by @benosteen in https://github.com/thegetty/lod-gateway/pull/445
* Dev 16217 landing page gives an error if database is empty by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/446
* Handling language tags in JSON-LD by @benosteen in https://github.com/thegetty/lod-gateway/pull/447
* Fix Entity Title Text Overflow Bug by @ramonemunoz in https://github.com/thegetty/lod-gateway/pull/448
* Update Orb to Version 3 – DEV-16254 by @bluebinary in https://github.com/thegetty/lod-gateway/pull/449
* oldest and newest AS links by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/450
* Dev=16219 implement rest delete by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/452
* Shifting to explicitly use /dev/shm for tmp space by @benosteen in https://github.com/thegetty/lod-gateway/pull/453
* Fix Memento Typos in Dashboard by @garciagregg in https://github.com/thegetty/lod-gateway/pull/454
* Fix memento typo in Python code by @garciagregg in https://github.com/thegetty/lod-gateway/pull/455
* Update Docker Compose settings for Fuseki by @workergnome in https://github.com/thegetty/lod-gateway/pull/442
* CircleCI deploy to JPC (stage) by @benosteen in https://github.com/thegetty/lod-gateway/pull/456
* CircleCI update + homepage JSON version by @benosteen in https://github.com/thegetty/lod-gateway/pull/457
* Bump gunicorn from 20.1.0 to 22.0.0 by @dependabot in https://github.com/thegetty/lod-gateway/pull/458
* Removing caching possibilities from CircleCI by @benosteen in https://github.com/thegetty/lod-gateway/pull/459
* Reformatting to black 24 by @benosteen in https://github.com/thegetty/lod-gateway/pull/460
* Fix Activity Stream Responses for Records that Never Existed – DEV-17363 by @elenamujal in https://github.com/thegetty/lod-gateway/pull/463
* Bump flask-cors from 3.0.10 to 4.0.1 by @dependabot in https://github.com/thegetty/lod-gateway/pull/461
* Bump requests from 2.31.0 to 2.32.0 by @dependabot in https://github.com/thegetty/lod-gateway/pull/462
* Adding the skip-to-datetime API call for the main activity-stream by @benosteen in https://github.com/thegetty/lod-gateway/pull/464
* Homepage fixes when db empty by @benosteen in https://github.com/thegetty/lod-gateway/pull/465
* Adding lod-gateway-media-jpc-l2 to JPCA deploy by @benosteen in https://github.com/thegetty/lod-gateway/pull/466
* Not prefixing 'id' values that contain ':' if it has a valid scheme by @benosteen in https://github.com/thegetty/lod-gateway/pull/467
* Bugfix on subaddressing on deleted records by @benosteen in https://github.com/thegetty/lod-gateway/pull/468
* Small auth cleanup by @benosteen in https://github.com/thegetty/lod-gateway/pull/469
* Marking datetime when startup script starts + skip flask db upgrade on demand by @benosteen in https://github.com/thegetty/lod-gateway/pull/470
* Bump flask-cors from 4.0.1 to 5.0.0 by @dependabot in https://github.com/thegetty/lod-gateway/pull/471

## New Contributors
* @elenamujal made their first contribution in https://github.com/thegetty/lod-gateway/pull/463

**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v2.5.3...v2.6.0
=======================================

v2.5.3 HTML Frontpage with fixes to Memento & Prefix search
v2.5.3 - Created: 2023-10-02T16:02:00Z

## What's Changed
* Hotfix - prefix search by @benosteen in https://github.com/thegetty/lod-gateway/pull/415
* Simple hosting without an application root by @benosteen in https://github.com/thegetty/lod-gateway/pull/416
* Keepalive option by @benosteen in https://github.com/thegetty/lod-gateway/pull/417
* Keepalive by @benosteen in https://github.com/thegetty/lod-gateway/pull/418
* Dev 15801 create home page for lod gateway by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/419
* changed style.css location by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/420
* styles moved in template file by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/421
* dashboard route added by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/422
* Added Material Design and Custom Styles by @ramonemunoz in https://github.com/thegetty/lod-gateway/pull/423
* Dev 15842 use env to fill links by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/424
* Readme modified for Link Bank by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/425
* Dev 15801 lod gateway version by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/426
* Removed LOD Gateway from Page Title by @ramonemunoz in https://github.com/thegetty/lod-gateway/pull/428
* Added New Disabled State for Badge Indicators by @ramonemunoz in https://github.com/thegetty/lod-gateway/pull/429
* General Styling and Word Capitalizing by @ramonemunoz in https://github.com/thegetty/lod-gateway/pull/430
* Programmatically Set the Word From Change to Changes Depending on a Value  by @ramonemunoz in https://github.com/thegetty/lod-gateway/pull/431
* Added Margin Top to Align Items by @ramonemunoz in https://github.com/thegetty/lod-gateway/pull/432
* write_version location changed by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/427
* revert version to local file by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/433
* copy version.txt to image by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/434
* copy version.txt by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/435
* change version capitalization by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/436
* Sort key setting by @benosteen in https://github.com/thegetty/lod-gateway/pull/440
* Bump gevent from 22.10.2 to 23.9.1 by @dependabot in https://github.com/thegetty/lod-gateway/pull/439
* Memento TimeMap - make application/link-format the default by @benosteen in https://github.com/thegetty/lod-gateway/pull/441
* Revise README File for Open Sourcing – DEV-16094 by @bluebinary in https://github.com/thegetty/lod-gateway/pull/438

## New Contributors
* @ramonemunoz made their first contribution in https://github.com/thegetty/lod-gateway/pull/423

**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v2.5.2...v2.5.3
=======================================

v2.5.2 Hotfix - nquads regex
v2.5.2 - Created: 2023-08-01T16:14:51Z

Combinations of BNode subject/objects with bnode named graphs were being missed by the previous regex, causing a resource to fail being expanded (as the nquads was not being successfully converted to ntriples in this specific case)

## What's Changed
* Updating the quads regex to handle bnodes in the RDFLib format by @benosteen in https://github.com/thegetty/lod-gateway/pull/413


**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v2.5.1...v2.5.2
=======================================

v2.5.1 PyLD dethroning
v2.5.1 - Created: 2023-07-19T23:14:17Z

The huge parse and reserialization times of large resources using PyLD is a huge problem. RDFLib v6+ has a json-ld parser and reserializer that seems to be functionally identical to the basic uses of PyLD. It does not handle framing, but this is not something used in the LOD Gateway application. In tests, a large (14MB) JSON-LD document took between 207-235 seconds to parse using PyLD. The same document took ~3s usig RDFLib. The ntriples output from both parsed forms were identical.

This release adds the ability to switch to use RDFLib entirely for the parsing and reserialization functionality in the gateway. The environment variable USE_PYLD_REFORMAT controls this - it currently defaults to true and will use PyLD. Set it explicitly to "false" to make the application only use RDFLib for handling the JSON-LD both on ingest and on reserialization. 

## What's Changed
* Yet another pyld workaround by @benosteen in https://github.com/thegetty/lod-gateway/pull/406
* Adding a default large timeout parameter of 600 by @benosteen in https://github.com/thegetty/lod-gateway/pull/407
* RDFlib parsing as an option by @benosteen in https://github.com/thegetty/lod-gateway/pull/408
* Versions of JSON-LD should also accept content negotiation by @benosteen in https://github.com/thegetty/lod-gateway/pull/409
* Version accept-datetime redirect fix by @benosteen in https://github.com/thegetty/lod-gateway/pull/410


**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v2.5...v2.5.1
=======================================

v2.5 Gunicorn and JSON Logging
v2.5 - Created: 2023-07-17T18:09:10Z

Switches from the uWSGI deployment to use Gunicorn. Also includes options for JSON formatted log messages for status and access logs, as well as a small fix for the basegraph handling.

## What's Changed
* Test mode basegraph by @benosteen in https://github.com/thegetty/lod-gateway/pull/392
* Tweaks to the uwsgi to see if it helps by @benosteen in https://github.com/thegetty/lod-gateway/pull/393
* Adding timing log information for upstream SPARQL service calls by @benosteen in https://github.com/thegetty/lod-gateway/pull/394
* Logging sparql calls by @benosteen in https://github.com/thegetty/lod-gateway/pull/395
* Adding some better than defaults to the keep alive by @benosteen in https://github.com/thegetty/lod-gateway/pull/396
* Not sure why it's missing these packages by @benosteen in https://github.com/thegetty/lod-gateway/pull/397
* Switching to 75s keep alive to match nginx by @benosteen in https://github.com/thegetty/lod-gateway/pull/398
* Fixing a bug with the base graph by @benosteen in https://github.com/thegetty/lod-gateway/pull/399
* Changed local thesaurus option by @garciagregg in https://github.com/thegetty/lod-gateway/pull/401
* Gunicorn migration by @benosteen in https://github.com/thegetty/lod-gateway/pull/400
* Changing default worker/threads by @benosteen in https://github.com/thegetty/lod-gateway/pull/402
* Switching some small defaults to new values by @benosteen in https://github.com/thegetty/lod-gateway/pull/403
* Access Logs as JSON via Env variable control by @benosteen in https://github.com/thegetty/lod-gateway/pull/404
* Gunicorn JSON log tweaks by @benosteen in https://github.com/thegetty/lod-gateway/pull/405


**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v2.4.1...v2.5
=======================================

Cache Control
v2.4.1 - Created: 2023-06-23T22:28:56Z

Hotfix to include 'Cache-Control: no-cache' with every request, to try to get anything downstream from trying to cache resources without checking.

## What's Changed
* Adding 'Cache-control: no-cache' to all responses by @benosteen in https://github.com/thegetty/lod-gateway/pull/390
* Turning off strict mode to debug in staging by @benosteen in https://github.com/thegetty/lod-gateway/pull/391


**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v2.4...v2.4.1
=======================================

RDF improvements v2.4 
v2.4 - Created: 2023-06-14T00:25:03Z

## What's Changed
* Base graph change log warning in wrong place by @benosteen in https://github.com/thegetty/lod-gateway/pull/382
* Dev 14133 by @ViktorGetty in https://github.com/thegetty/lod-gateway/pull/383
* Fix for when the nquads export includes ntriples mixed in by @benosteen in https://github.com/thegetty/lod-gateway/pull/384
* Force all graph replacements to be triples by @benosteen in https://github.com/thegetty/lod-gateway/pull/385
* Bump requests from 2.27.1 to 2.31.0 by @dependabot in https://github.com/thegetty/lod-gateway/pull/387
* Bump flask from 2.0.3 to 2.3.2 by @dependabot in https://github.com/thegetty/lod-gateway/pull/386
* Shorter fix for the datetime comparison for TimeGate Memento API by @benosteen in https://github.com/thegetty/lod-gateway/pull/388
* Adding the custom doc loader to the RDF handling. by @benosteen in https://github.com/thegetty/lod-gateway/pull/389


**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v2.3...v2.4
=======================================

RDF Enhancements; Momento Bug Fixes; uWSGI Performance Enhancements
v2.3 - Created: 2022-12-16T00:13:11Z

## What's Changed
* Updating versions, and black linter by @benosteen in https://github.com/thegetty/lod-gateway/pull/366
* Added TMS L1 to staging deploy by @garciagregg in https://github.com/thegetty/lod-gateway/pull/368
* Add TMS L1 to prod deploy by @garciagregg in https://github.com/thegetty/lod-gateway/pull/369
* Sparql -> openjdk:20 by @benosteen in https://github.com/thegetty/lod-gateway/pull/370
* Added staging L1 and L2 instances for JPC data to the deployment by @garciagregg in https://github.com/thegetty/lod-gateway/pull/371
* Adding Consonance L1 to staging and prod deployment by @garciagregg in https://github.com/thegetty/lod-gateway/pull/372
* Refresh/revert Graph API call by @benosteen in https://github.com/thegetty/lod-gateway/pull/373
* Adding a more refined uwsgi.ini file, with worker scaling by @benosteen in https://github.com/thegetty/lod-gateway/pull/374
* Optional Prev Link Header by @benosteen in https://github.com/thegetty/lod-gateway/pull/375
* RDF Transforms by @benosteen in https://github.com/thegetty/lod-gateway/pull/376
* Base Graph Filter by @benosteen in https://github.com/thegetty/lod-gateway/pull/377
* Suppress basegraph from the activitystream by @benosteen in https://github.com/thegetty/lod-gateway/pull/378
* Trying to switch uwsgi to lazy mode by @benosteen in https://github.com/thegetty/lod-gateway/pull/379
* Fixing the first/last in the timemap list by @benosteen in https://github.com/thegetty/lod-gateway/pull/380
* Relative id flag by @benosteen in https://github.com/thegetty/lod-gateway/pull/381


**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v2.2...v2.3
=======================================

SQLAlchemy Optimizations v2.2
v2.2 - Created: 2022-06-30T21:18:29Z

- More use of default and explicit deferred queries for ORM objects, as well as `load_only` for Memento-based requests
- New index to speed up common queries
- Removal of unused indexes to increase write performance

## What's Changed
* DEV-12717 Version SQLAlchemy optimizing by @benosteen in https://github.com/thegetty/lod-gateway/pull/365


**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v2.1...v2.2
=======================================

Rollback activity-stream to fixed width offset
v2.1 - Created: 2022-04-29T18:22:05Z

The query was changed to try to accommodate activity-stream event deletions without leaving gaps in the activity-stream. This was not performant enough at the larger scale without removing events, so rolling back to the original fixed-width query. 

Deletions of old duplicated or stale events will leave gaps in the record and there will also not be a reduction in the number of pages a client will have to retrieve to get the whole history.

## What's Changed
* Revert to fixed offset queries by @benosteen in https://github.com/thegetty/lod-gateway/pull/364


**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v2.0...v2.1
=======================================

Full Versioning, Subaddressing and Activity-stream updates
v2.0 - Created: 2022-04-26T22:06:27Z

Main new features:

- Full versioning, with Memento support
- Subaddressing (relative URIs within documents stored in the LOD Gateway will resolve if turned on)
- Activity-stream truncation API (per entity)

## What's Changed
* Shifted to python 3.9, updated all main dependencies by @benosteen in https://github.com/thegetty/lod-gateway/pull/353
* Should have been math.ceil not int by @benosteen in https://github.com/thegetty/lod-gateway/pull/355
* Full versioning by @benosteen in https://github.com/thegetty/lod-gateway/pull/354
* Hotfix - fixing a memento date by @benosteen in https://github.com/thegetty/lod-gateway/pull/358
* Per-entity activitystreams, and truncation by @benosteen in https://github.com/thegetty/lod-gateway/pull/357
* Tweaking the query to be more perfomant at the end of an activitystream by @benosteen in https://github.com/thegetty/lod-gateway/pull/359
* Optimize activitystream query by @benosteen in https://github.com/thegetty/lod-gateway/pull/360
* Adding subaddressing functionality by @benosteen in https://github.com/thegetty/lod-gateway/pull/356
* Changing orb version to latest v2 by @benosteen in https://github.com/thegetty/lod-gateway/pull/362


**Full Changelog**: https://github.com/thegetty/lod-gateway/compare/v1.1.0...v1.2
=======================================

Sparql Update Refactor
v1.1.0 - Created: 2022-03-05T17:59:01Z

- Refactoring of Sparql update functionality in ingest
- Enhanced error reporting in ingest with Retry-After added to response header when graph store is overloaded
- Local thesaurus modeling switched to Linked.Art from SKOS
=======================================

Sparql POST Return Headers
v1.0.8 - Created: 2022-02-09T16:15:03Z

Return headers from graph store with Sparql POST request
=======================================

Sparql POST Modifications
v1.0.7 - Created: 2022-02-09T01:10:58Z

Passes entire content of POST request
=======================================

Sparql Request Debugging
v1.0.6 - Created: 2022-02-08T20:20:23Z

Added debugging for POST requests coming to the Sparql endpoint
=======================================

Glob listing update
v1.0.5 - Created: 2021-12-21T00:33:27Z

Listing the contents of the LOD Gateway by using a wildcard suffix (*) now only includes current versions of resources.
=======================================

Add Local Thesaurus to Production Deployment
v1.0.4 - Created: 2021-10-15T00:09:36Z

Includes the local thesaurus in the production deployment CI
=======================================

Local Thesaurus Functionality
v1.0.3 - Created: 2021-10-14T23:00:29Z

Added functionality for creating a local thesaurus with an in-memory SQLlite database. Local thesaurus data is loaded at container startup from a CSV file located at URL set in the **LOCAL_THESAURUS_URL** envar.
=======================================

Update SPARQL HTTP Error Handling
v1.0.2 - Created: 2021-09-13T19:16:08Z

Passes HTTP error to client from graph store
=======================================

Activity Stream Update
v1.0.1 - Created: 2021-09-03T00:42:43Z

- added "endTime" property to activity stream items to eventually replace "created" in a later version
- improved error reporting for invalid JSON ingest payloads
=======================================

LOD Gateway Version 1.0.0
v1.0.0 - Created: 2021-08-10T19:05:21Z

First tagged version of the LOD Gateway.
=======================================

