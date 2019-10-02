# LOD Gateway Changelog

**2019-10-01**

* DEV-2589: Added this `CHANGELOG.md` file to the project to keep track of changes just like this.
* DEV-2578: Removed trailing slash from Person biography statement AAT term
* DEV-2588: Removed Inhabited Place AAT Term from Object's `took_place_at` mapping, and Person's `birth` and `death` mappings as it was not adding additional information, but was rather standing in for more specific terms such as City or Country, in lieu of the fact that current place data has not been reconciled at the source. 
