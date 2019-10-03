# Linked Open Data (LOD) Gateway Change Log

Any notable changes to the LOD Gateway that affect either functionality or output will be documented in this file (the format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)).

## [Unreleased] 2019-10-01
### Added

+ This `CHANGELOG.md` file to the project to keep track of changes just like this.
+ A `format` property to `Object` Description and `Person` Biography `LinguisticObject` entities within `Object` and `Person` records; currently mapping the `text/html` MIME type of the content, later to be modified to `text/markdown` once the conversion of descriptions and biographies has been completed.

### Changed

* Converted DOR/TMS integer record IDs to their string representations, to be consistent with other ID types and values.

### Removed

- Extraneous trailing slash from Person "Biography Statement" AAT term classification ID URL.
- "Inhabited Place" AAT Term from Object's `took_place_at` mapping, and Person's `birth` and `death` mappings as it was not adding additional information, but was rather standing in for more specific terms such as City or Country, in lieu of the fact that current place data has not been reconciled at the source. 
- "Dates (Spans of Time)" AAT Term (300404439) from `TimeSpan` entities and `TimeSpan`'s `identified_by` `Name` entity.
- "Legal Concept" AAT Term () from Credit Line & Copyright Statement as these now have their own specific AAT terms "Credit Line" (300435418) and "Copyright/Legal Statement" (300435434) respectively.
- Incorrect "Dimensions Statement" AAT term (300266036) which actually references the broader concept of "Dimensions (Measurements)"; this is now superseded by the newly added, correct and specific "Dimensions Description" AAT term (300435430).
- Incorrect "Materials Statement" AAT term (300010358) which actually references the broader concept of "Materials (Substances)"; this is now supersede by the newly added, correct and specific "Materials Description" AAT term (300435429).
- "Signatures (Names)" AAT term (300028705) from Signatures; this is now supersede by the newly added, correct and specific "Signatures Description" AAT term (300435415).
