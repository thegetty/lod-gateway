# Linked Open Data (LOD) Gateway Change Log

Any notable changes to the LOD Gateway that affect either functionality or output will be documented in this file (the format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)).

## [Unreleased] 2019-11-15

## Changed

* Consolidate the `classified_as` IDs for the DOR and TMS record IDs emitted into the JSON-LD, using one unique `classified_as` ID for each of the three DOR and TMS ID types [[DEV-3020](https://jira.getty.edu/browse/DEV-3020)]:

	* For the DOR integer ID, these will be consolidated from the current two IDs:
		* https://data.getty.edu/museum/ontology/linked-data/dor/identifier
		* https://data.getty.edu/museum/ontology/linked-data/integer-identifier

	* Into a single `classified_as` ID combining the two concepts:
		* https://data.getty.edu/museum/ontology/linked-data/dor/integer-identifier

	* For the DOR UUID, these will be consolidated from the current two IDs:
		* https://data.getty.edu/museum/ontology/linked-data/dor/identifier
		* https://data.getty.edu/museum/ontology/linked-data/universally-unique-identifier

	* Into a single `classified_as` ID combining the two concepts:
		* https://data.getty.edu/museum/ontology/linked-data/dor/universally-unique-identifier

	* For the TMS integer ID, these will be consolidated from the current two IDs:
		* https://data.getty.edu/museum/ontology/linked-data/tms/identifier
		* https://data.getty.edu/museum/ontology/linked-data/integer-identifier

	* Into a single `classified_as` ID combining the two concepts:
		* https://data.getty.edu/museum/ontology/linked-data/tms/integer-identifier

## [Unreleased] 2019-11-13

### Changed

* Changed the mapping of an Object's "Place Created" property. This was formerly provided as a reference to an incomplete `Place` entity via the the `produced_by` property's `took_place_at` clause. However, as we do not currently have reconciled Place Created data, the verbatim Place Created display string is now more correctly provided via the `content` value of a `LinguisticObject` within the `produced_by` property's `referred_to_by` clause. This new Place Created `LinguisticObject` is classified with the AAT "Place Names" (300404655) and "Brief Text" (300418049) terms, as well as a custom "Place Created" classification. In the future when we have access to reconciled Place Created metadata that would allow linking to [The Getty Thesaurus of Geographic Names ® (TGN)](http://www.getty.edu/research/tools/vocabularies/tgn/about.html), we will do so via the `took_place_at` property, in addition to continuing to provide access to the Place Created display string via the newly added `LinguisticObject` [[DEV-2979](https://jira.getty.edu/browse/DEV-2979)].

* Changed the `Production` entity URL pattern from `.../activity/production/...` to just `.../production/...` for clarity [[DEV-3017](https://jira.getty.edu/browse/DEV-3017)].

### Added

+ Added a mapping for an Object's Place Found verbatim display string. This has been provided, where available, via the `content` property of a new `LinguisticObject`, which has been added to an Object record's top-level `referred_to_by` property. The Place Found `LinguisticObject` has been classified with the AAT "Place Names" (300404655) and "Brief Text" (300418049) terms, as well as a custom "Place Found" classification, to allow it to be distinguished from other Place display strings and other `LinguisticObject` instances [[DEV-2980](https://jira.getty.edu/browse/DEV-2980)].

+ Added a mapping for an Object's Place Depicted verbatim display string. This has been provided, where available, via the `content` property of a new `LinguisticObject`, which has been added to an Object record's top-level `shows` property, via its `VisualItem`. The Place Depicted `LinguisticObject` is associated with the `VisualItem` via its `referred_to_by` property, and has been classified with the AAT "Place Names" (300404655) and "Brief Text" (300418049) terms, as well as a custom "Place Depicted" classification, to allow it to be distinguished from other Place display strings and other `LinguisticObject` instances [[DEV-2981](https://jira.getty.edu/browse/DEV-2981)].

## [Unreleased] 2019-10-14

### Changed

* Changed Custom Classification Ontology/Vocabulary Term Base URLs from `http://vocab.getty.edu/internal/ontologies/linked-data` to `https://data.getty.edu/museum/ontology/linked-data` [[DEV-2605](https://jira.getty.edu/browse/DEV-2605)].

* Changed the `Source Credit Line` classification, removing the "Primary Sources" (300311936) AAT term, and replacing with the more suitable "Sources (General Concept)" (300404764) AAT term [[DEV-2631](https://jira.getty.edu/browse/DEV-2631)]. The `Source Credit Line` continues to carry the "Credit Line" (300435418) AAT term.

* Modified date values expressed via `TimeSpan` entities to ensure they are compliant with the `xsd:Date` format. Thus a date previously expressed as `2019-10-14 01:02:03` will now be expressed as `2019-10-14T01:02:03` – notice the literal `T` now used as a separator between the date and time components of the string [[DEV-2610](https://jira.getty.edu/browse/DEV-2610)].

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
