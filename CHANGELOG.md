# Linked Open Data (LOD) Gateway Change Log

This document details any significant changes to the LOD Gateway that affect either functionality or output. In most cases these changes will reference their related Jira tickets.

## [Unreleased] 2019-10-07

### Added

+ Added a timeout for API requests, configured to 90 seconds for the connection and read portions of each request, to protect against network outages. This has been configured via the `requests` library `timeout` property. The default for the `requests` library is that there is no timeout, as such the library would otherwise wait indefinitely for a response. This change only affects the data transformation process, and does not have any impact on the web services of the LOD Gateway, which include the Activity Stream and record retrieval endpoints [[DEV-2606](https://jira.getty.edu/browse/DEV-2606)].

+ Added the previously omitted `conforms_to` property to each relevant `Object` entity's `subject_of` property mapping for related IIIF manifests; this now brings the mapping of IIIF manifests into conformance with the Linked.art [documentation](https://linked.art/model/digital/#iiif-manifests) for these resources. The property was previously omitted because CROM does not currently support adding a `conforms_to` property to `InformationObject` entities, contrary to the referenced Linked.art documentation. As such the `conforms_to` property had to be added to the `InformationObject` entity outside of CROM. When CROM is updated to offer support for the `conforms_to` property, the code will be updated to use CROM to map this property instead [[DEV-2628](https://jira.getty.edu/browse/DEV-2628)].

### Changed

* The mapping of `Object` numbers has been changed. Depending on the `Object` record there may only be one number mapped – its accession number, which will be classified as an "Accession Number" (300312355), and will also be classified as the "Preferred Term" (300404670) when it is the only number mapped; alternatively, if the `Object` has a display number that is different to its accession number, this alternate number will be included as well as the accession number. The accession number will still of course continue to be classified as an "Accession Number" (300312355), but in this case, the display number, not the accession number, would be classified as the "Preferred Term" (300404670), to denote the preference for using it as the display number. In cases where an `Object` record represents a Manuscript from the Getty's Manuscripts Department, the special Manuscript Department number, e.g. _Ms. 20_, will also be mapped in addition to the accession number, e.g. _86.MV.527_, and its display number, e.g. _Ms. 20 (86.MV.527)_. The Manuscript Department number will be classified using a custom term, "Getty Manuscript Number", as no such specific term is available from AAT. In addition to the specific classifiers denoting the type of each `Object` number, all numbers will also carry the "Identification Number" (300404626) classification so that they can be extracted from an `Object` record's `identified_by` list holistically if needed. Lastly, in all cases, one should default to using the `Object` number ("Identification Number") classified as the "Preferred Term" (300404670) for display purposes, while all of the provided numbers should ideally also be indexed so that an `Object` could be found via any of its associated numbers [[DEV-2630](https://jira.getty.edu/browse/DEV-2630)].

* The mapping for each `Object` record's `current_owner` property has been changed, so that the `current_owner` now references a `Group` record representing the J. Paul Getty Museum, rather than referencing the J. Paul Getty Museum via its ULAN ID URL, as was the case previously. Mapping the `current_owner` to the `Group` record brings this relationship into conformance with other `Actor` relationships in the data. The referenced `Group` record instead carries the J. Paul Getty Museum's ULAN ID, via its `exact_match` property, which follows the same pattern as used for other `Actor` (`Group` or `Person`) records that have known ULAN entries [[DEV-2608](https://jira.getty.edu/browse/DEV-2608)].

### Removed

- Removed the `member_of` property from the `current_keeper` mapping for `Object` records, as this membership information is also available within the referenced `Actor` (`Group` or `Person`) record denoted by the `current_keeper` relationship, so was superfluous here [[DEV-2626](https://jira.getty.edu/browse/DEV-2626)].

- Removed the `acquired_title_through` property of the `current_owner` property mapping for `Object` entities. It was determined that the `acquired_title_through` property currently does not carry any additional meaningful metadata, thus it was decided to remove it until such a time in the future when additional information can be mapped via this property [[DEV-2069](https://jira.getty.edu/browse/DEV-2069)].

## [Unreleased] 2019-10-01

### Added

+ This `CHANGELOG.md` file to the project to keep track of changes just like this [[DEV-2589](https://jira.getty.edu/browse/DEV-2592)].

### Changed

* Converted DOR/TMS integer record IDs to their string representations, to be consistent with other ID types and values [[DEV-2592](https://jira.getty.edu/browse/DEV-2592)].

### Removed

- Extraneous trailing slash from Person "Biography Statement" AAT term classification ID URL [[DEV-2578](https://jira.getty.edu/browse/DEV-2588)].

- "Inhabited Place" AAT term from Object's `took_place_at` mapping, and Person's `birth` and `death` mappings as it was not adding additional information, but was rather standing in for more specific terms such as City or Country, in lieu of the fact that current place data has not been reconciled at the source [[DEV-2588](https://jira.getty.edu/browse/DEV-2588)].

- "Dates (Spans of Time)" AAT term (300404439) from `TimeSpan` entities and `TimeSpan`'s `identified_by` `Name` entity [[DEV-2590](https://jira.getty.edu/browse/DEV-2590)].

- "Legal Concept" AAT term (300055547) from Credit Line & Copyright Statement as these now have their own specific AAT terms "Credit Line" (300435418) and "Copyright/Legal Statement" (300435434) respectively [[DEV-2591](https://jira.getty.edu/browse/DEV-2591)].

- Incorrect "Dimensions Statement" AAT term (300266036) which actually references the broader concept of "Dimensions (Measurements)"; this is now superseded by the newly added, correct and specific "Dimensions Description" AAT term (300435430) [[DEV-2593](https://jira.getty.edu/browse/DEV-2593)].

- Incorrect "Materials Statement" AAT term (300010358) which actually references the broader concept of "Materials (Substances)"; this is now superseded by the newly added, correct and specific "Materials Description" AAT term (300435429) [[DEV-2594](https://jira.getty.edu/browse/DEV-2594)].

- "Signatures (Names)" AAT term (300028705) from Signatures; this is now superseded by the newly added, correct and specific "Signatures Description" AAT term (300435415) [[DEV-2596](https://jira.getty.edu/browse/DEV-2596)].