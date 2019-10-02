# Linked Open Data (LOD) Gateway Change Log

This document details any significant changes to the LOD Gateway that affect either functionality or output. In most cases these changes will reference their related Jira tickets.

**2019-10-01**

* DEV-2589 – Added this `CHANGELOG.md` file to the project to keep track of changes just like this.
* DEV-2578 – Removed extraneous trailing slash from Person "Biography Statement" AAT term classification ID URL.
* DEV-2588 – Removed "Inhabited Place" AAT Term from Object's `took_place_at` mapping, and Person's `birth` and `death` mappings as it was not adding additional information, but was rather standing in for more specific terms such as City or Country, in lieu of the fact that current place data has not been reconciled at the source. 
* DEV-2590 – Removed "Dates (Spans of Time)" AAT Term (300404439) from `TimeSpan` entities and `TimeSpan`'s `identified_by` `Name` entity.
* DEV-2591 – Removed "Legal Concept" AAT Term () from Credit Line & Copyright Statement as these now have their own specific AAT terms "Credit Line" (300435418) and "Copyright/Legal Statement" (300435434) respectively.
* DEV-2592 – Conveted DOR/TMS integer record IDs to their string representations, to be consistent with other ID types and values.
* DEV-2593 – Removed the incorrect "Dimensions Statement" AAT term (300266036) which actaully references the borader concept of "Dimensions (Measurements)"; this is now superceeded by the newly added, correct and specific "Dimensions Description" AAT term (300435430).
* DEV-2594 – Removed the incorrect "Materials Statement" AAT term (300010358) which acutally references the broader concept of "Materials (Substances)"; this is now superceeed by the newly added, correct and specific "Materials Description" AAT term (300435429).
* DEV-2595 – Removed "Signatures (Names)" AAT term (300028705) from Signatures; this is now superceeed by the newly added, correct and specific "Signatures Description" AAT term (300435415).
* DEV-2596 – Added a new `format` property to `Object` Description and `Person` Biography `LinguisticObject` entities within `Object` and `Person` records; currently mapping the `text/html` MIME type of the content, later to be modified to `text/markdown` once the conversion of descriptions and biographies has been completed.