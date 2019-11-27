import os
import json
import uuid

# Import our application utility functions
from app.utilities import (
    get,
    has,
    debug,
    sprintf,
    date,
    hyphenatedStringFromSpacedString,
)

# Import our dependency injector
from app.di import DI

# Import our Museum Collection BaseTransformer class
from app.transformers.museum.collection.BaseTransformer import BaseTransformer

# Import the cromulent model for handling the assembly and export of our linked data
from cromulent.model import (
    factory,
    Identifier,
    Mark,
    HumanMadeObject as Object,
    Type,
    Person,
    Material,
    MeasurementUnit,
    Place,
    Dimension,
    Currency,
    ConceptualObject,
    TimeSpan,
    Actor,
    PhysicalThing,
    Language,
    LinguisticObject,
    InformationObject,
    Activity,
    Group,
    Name,
    MonetaryAmount,
    PropertyInterest,
    Destruction,
    AttributeAssignment,
    BaseResource,
    PhysicalObject,
    Acquisition,
    HumanMadeFeature,
    VisualItem,
    Set,
    PropositionalObject,
    Payment,
    Creation,
    Phase,
    Birth,
    Death,
    TimeSpan,
    Production,
    PropositionalObject as Exhibition,
)


class ArtifactTransformer(BaseTransformer):
    def activityStreamObjectTypes(self):
        """Provide a method for conveying the supported Activity Stream Object type names that this transformer will handle"""
        return [
            "Artifact",
        ]

    def resourceType(self):
        return "artifact"

    def entityType(self):
        """Provide a method for determining the correct target entity type"""
        return Object

    def entityName(self):
        """Provide a method for determining the correct target entity type name"""
        return "Object"

    def loadCultures(self):
        with open(
            os.path.dirname(os.path.abspath(__file__)) + "/./data/Cultures.json", "r"
        ) as file:
            content = file.read()

        if content:
            cultures = json.loads(content)

            if cultures:
                return cultures

        return None

    def loadMaterials(self):
        with open(
            os.path.dirname(os.path.abspath(__file__)) + "/./data/Materials.json", "r"
        ) as file:
            content = file.read()

        if content:
            materials = json.loads(content)

            if materials:
                return materials

        return None

    # Map Entity Label
    def mapEntityLabel(self, entity, data):
        entity._label = get(
            data, "display.title.display.value", default="Object(" + str(self.id) + ")"
        )

    # Map RightsStatements.org Assertion
    def mapRightsStatement(self, entity, data):
        assertion = get(data, "display.rights.display.value")
        if assertion:
            link = get(data, "display.rights.display.uri")
            if link:
                lobj = LinguisticObject()
                lobj.id = link
                lobj._label = "RightsStatements.org Rights Assertion"
                lobj.content = assertion

                # Map the "Rights Statement" classification
                lobj.classified_as = Type(
                    ident="http://vocab.getty.edu/aat/300055547",
                    label="Rights Statement",
                )

                # Map the "Brief Text" classification
                lobj.classified_as = Type(
                    ident="http://vocab.getty.edu/aat/300418049", label="Brief Text"
                )

                entity.referred_to_by = lobj

    # Map Copyright Statement
    def mapCopyrightStatement(self, entity, data):
        copyright = get(data, "display.copyright.display.value")
        if copyright:
            lobj = LinguisticObject()
            lobj.id = self.generateEntityURI(
                sub=["text", get(data, "display.copyright.uuid")]
            )
            lobj._label = "Copyright Statement"
            lobj.content = copyright

            # Map the "Copyright/Licensing Statement" classification
            lobj.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300435434",
                label="Copyright/Licensing Statement",
            )

            # Map the "Brief Text" classification
            lobj.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300418049", label="Brief Text"
            )

            entity.referred_to_by = lobj

    # Map Object, Source & Reproduction Credit Line Statements
    def mapCreditLineStatements(self, entity, data):
        creditlines = get(data, "display.creditlines")
        if isinstance(creditlines, dict) and len(creditlines) > 0:
            for index, key in enumerate(creditlines):
                creditline = creditlines[key]
                if creditline:
                    statement = get(creditline, "display.value")
                    if statement:
                        lobj = LinguisticObject()
                        lobj.id = self.generateEntityURI(
                            sub=["text", get(data, "uuid")]
                        )
                        lobj.content = statement

                        # Map the "Credit Line" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300435418",
                            label="Credit Line",
                        )

                        if get(creditline, "subtype") == "OBJECT CREDIT LINE":
                            lobj._label = "Object Credit Line"
                            # Map the "Artifacts (Object Genre)" classification to denote this as the Object Credit Line
                            lobj.classified_as = Type(
                                ident="http://vocab.getty.edu/aat/300117127",
                                label="Artifacts (Object Genre)",
                            )
                        elif get(creditline, "subtype") == "SOURCE CREDIT LINE":
                            lobj._label = "Source Credit Line"
                            # Map the "Sources (General Concept)" classification to denote this as the Source Credit Line
                            lobj.classified_as = Type(
                                ident="http://vocab.getty.edu/aat/300404764",
                                label="Sources (General Concept)",
                            )
                        elif get(creditline, "subtype") == "REPRODUCTION CREDIT LINE":
                            lobj._label = "Reproduction Credit Line"
                            # Map the "Reproductions (Derivative Items)" classification to denote this as the Reproduction Credit Line
                            lobj.classified_as = Type(
                                ident="http://vocab.getty.edu/aat/300015643",
                                label="Reproductions (Derivative Items)",
                            )

                        # Map the "Brief Text" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300418049",
                            label="Brief Text",
                        )

                        entity.referred_to_by = lobj

    # Map Classifications
    def mapClassifications(self, entity, data):
        # Map the standard "Artwork" classification for all Objects (Artifacts) in this data set
        entity.classified_as = Type(
            ident="http://vocab.getty.edu/aat/300133025", label="Artwork"
        )

        # Set defined Object Classification if available
        classification = get(data, "display.classification")
        if classification and has(classification, "classification.id"):
            # debug(classification, format="JSON")

            entity.classified_as = Type(
                ident=get(classification, "classification.id"),
                label=get(classification, "classification.label"),
            )

    def getNumber(self, mnemonic=None, keypath=None):
        if mnemonic:
            numbers = get(self.data, "display.numbers")
            if isinstance(numbers, dict) and len(numbers) > 0:
                for key in numbers:
                    number = numbers[key]
                    if isinstance(number, dict):
                        if get(number, "mnemonic") == mnemonic:
                            if isinstance(keypath, str) or isinstance(keypath, list):
                                return get(number, keypath)
                            else:
                                return number

        return None

    # Map Accession Number
    def mapAccessionNumber(self, entity, data):
        numbers = get(data, "display.numbers")
        if isinstance(numbers, dict) and len(numbers) > 0:
            display_number = self.getNumber(
                mnemonic="DISPLAY NUMBER", keypath="display.value"
            )

            for key in numbers:
                number = numbers[key]
                if isinstance(number, dict):
                    if get(number, "mnemonic") == "OBJECT NUMBER":
                        number_id = get(number, "uuid")
                        if number_id:
                            identifier = Identifier()
                            identifier.id = self.generateEntityURI(
                                sub=["identifier", number_id]
                            )
                            identifier._label = "Accession Number"
                            identifier.content = get(number, "display.value")

                            # Map the "Identification Number" classification
                            identifier.classified_as = Type(
                                ident="http://vocab.getty.edu/aat/300404626",
                                label="Identification Number",
                            )

                            # Map the "Accession Number" classification
                            identifier.classified_as = Type(
                                ident="http://vocab.getty.edu/aat/300312355",
                                label="Accession Number",
                            )

                            # If the Accession and Display Numbers are the same, mark the Accession Number as the Preferred Term
                            if isinstance(display_number, str) and (
                                identifier.content == display_number
                            ):
                                # Map the "Preferred Term" classification
                                # This is important as it denotes this number is the preferred number associated with the work
                                identifier.classified_as = Type(
                                    ident="http://vocab.getty.edu/aat/300404670",
                                    label="Preferred Term",
                                )

                            entity.identified_by = identifier

    # Map Display Number
    def mapDisplayNumber(self, entity, data):
        numbers = get(data, "display.numbers")
        if isinstance(numbers, dict) and len(numbers) > 0:
            accession_number = self.getNumber(
                mnemonic="OBJECT NUMBER", keypath="display.value"
            )
            display_number = self.getNumber(
                mnemonic="DISPLAY NUMBER", keypath="display.value"
            )

            # If the Accession and Display Numbers are the same, skip mapping the Display Number
            if accession_number == display_number:
                return

            for key in numbers:
                number = numbers[key]
                if isinstance(number, dict):
                    if get(number, "mnemonic") == "DISPLAY NUMBER":
                        number_id = get(number, "uuid")
                        if number_id:
                            identifier = Identifier()
                            identifier.id = self.generateEntityURI(
                                sub=["identifier", number_id]
                            )
                            identifier._label = "Display Number"
                            identifier.content = get(number, "display.value")

                            # Map the "Identification Number" classification
                            identifier.classified_as = Type(
                                ident="http://vocab.getty.edu/aat/300404626",
                                label="Identification Number",
                            )

                            # Map the "Preferred Term" classification
                            # This is important as it denotes this number is the preferred number associated with the work
                            identifier.classified_as = Type(
                                ident="http://vocab.getty.edu/aat/300404670",
                                label="Preferred Term",
                            )

                            entity.identified_by = identifier

    # Map Manuscript Number
    def mapManuscriptNumber(self, entity, data):
        department = get(data, "display.department.mnemonic")
        if isinstance(department, str) and department == "MANUSCRIPTS":
            numbers = get(data, "display.numbers")
            if isinstance(numbers, dict) and len(numbers) > 0:
                for key in numbers:
                    number = numbers[key]
                    if isinstance(number, dict):
                        if get(number, "mnemonic") == "MANUSCRIPT NUMBER":
                            number_id = get(number, "uuid")
                            if number_id:
                                identifier = Identifier()
                                identifier.id = self.generateEntityURI(
                                    sub=["identifier", number_id]
                                )
                                identifier._label = "Manuscript Number"
                                identifier.content = get(number, "display.value")

                                # Map the "Identification Number" classification
                                identifier.classified_as = Type(
                                    ident="http://vocab.getty.edu/aat/300404626",
                                    label="Identification Number",
                                )

                                # Map the "Getty Manuscript Number" classification
                                identifier.classified_as = Type(
                                    ident="https://data.getty.edu/museum/ontology/linked-data/tms/object/number/manuscript",
                                    label="Getty Manuscript Number",
                                )

                                entity.identified_by = identifier

    # Map Primary Title
    def mapPrimaryTitle(self, entity, data):
        title = get(data, "display.title.display.value")
        if title:
            title_id = get(data, "display.title.uuid")
            if title_id:
                name = Name()
                name.id = self.generateEntityURI(sub=["name", title_id])
                name._label = "Primary Title"
                name.content = title

                # Map the "Title (General, Names)" classification to denote this as a title
                # This is important as it denotes this title is the primary title associated with the work
                name.classified_as = Type(
                    ident="http://vocab.getty.edu/aat/300417193",
                    label="Titles (General, Names)",
                )

                # Map the "Preferred Term" classification
                # This is important as it denotes this title is the preferred (or primary) title associated with the work
                name.classified_as = Type(
                    ident="http://vocab.getty.edu/aat/300404670", label="Preferred Term"
                )

                entity.identified_by = name

    # Map Alternate Titles
    def mapAlternateTitles(self, entity, data):
        titles = get(data, "display.titles")
        if titles and len(titles) > 0:
            for key in titles:
                title = titles[key]
                if title:
                    value = get(title, "display.value")
                    if value:
                        id = get(title, "uuid")
                        if id:
                            # Exclude the following title subtypes...
                            subtype = get(title, "subtype")
                            if subtype and subtype not in [
                                "PRIMARY TITLE",
                                "GETTYGUIDE SEARCH TITLE",
                                "GETTYGUIDE MIDDLE TITLE",
                                "GETTYGUIDE SHORT TITLE",
                                "GETTYGUIDE PAGING SHORT TITLE",
                            ]:
                                name = Name()
                                name.id = self.generateEntityURI(sub=["name", id])
                                name._label = get(
                                    title, "display.label", default="Alternate Title"
                                )
                                name.content = value

                                # Map the "Title (General, Names)" classification to denote this as a title
                                name.classified_as = Type(
                                    ident="http://vocab.getty.edu/aat/300417193",
                                    label="Titles (General, Names)",
                                )

                                # Classify the title as an Alternate Title
                                name.classified_as = Type(
                                    ident="http://vocab.getty.edu/aat/300417227",
                                    label="Alternate Title",
                                )

                                # Classify the title using the subtype provided by TMS; in the future hopefully we can add or replace these
                                # home-grown classifications with something official from AAT or another controlled vocabulary...
                                name.classified_as = Type(
                                    ident="https://data.getty.edu/museum/ontology/linked-data/tms/object/titles/"
                                    + hyphenatedStringFromSpacedString(subtype.lower()),
                                    label=subtype.title(),
                                )

                                remarks = get(title, "remarks")
                                if remarks:
                                    name.classified_as = Type(
                                        ident="https://data.getty.edu/museum/ontology/linked-data/tms/object/titles/"
                                        + hyphenatedStringFromSpacedString(
                                            remarks.lower()
                                        ),
                                        label=remarks.title(),
                                    )

                                related = get(title, "related")
                                if related:
                                    groups = get(related, "groups")
                                    if groups:
                                        for group in groups:
                                            if get(group, "type") == "EXHIBITION":
                                                activity = Activity(
                                                    ident=self.generateEntityURI(
                                                        entity=Activity,
                                                        id=get(group, "uuid"),
                                                    ),
                                                    label=get(group, "display.value"),
                                                )
                                                if activity:
                                                    activity.classified_as = Type(
                                                        ident="http://vocab.getty.edu/aat/300054766",
                                                        label="Exhibitions (Events)",
                                                    )

                                                    name.classified_as = Type(
                                                        ident="http://vocab.getty.edu/aat/300417207",
                                                        label="Exhibition Title (Work Title)",
                                                    )

                                                    name.used_for = activity

                                entity.identified_by = name

    # Map Object Description
    def mapDescription(self, entity, data):
        description = get(data, "display.description.display.value")
        if description:
            id = get(data, "display.description.uuid")
            if id:
                lobj = LinguisticObject()
                lobj.id = self.generateEntityURI(sub=["description", id])
                lobj.content = description

                # Map the "Description" classification
                lobj.classified_as = Type(
                    ident="http://vocab.getty.edu/aat/300080091", label="Description"
                )

                # Map the "Brief Text" classification
                lobj.classified_as = Type(
                    ident="http://vocab.getty.edu/aat/300418049", label="Brief Text"
                )

                entity.referred_to_by = lobj

    # Map Object Culture Statement/Type
    def mapCulture(self, entity, data):
        culture = get(data, "display.culture.display.value")
        if culture:
            id = get(data, "display.culture.uuid")
            if id:
                # Add a LinguisticObject via the "referred_to_by" property on the object
                # Add a classified_as to the LinguisticObject of type http://vocab.getty.edu/aat/300055768 (culture)

                lobj = LinguisticObject()
                lobj.id = self.generateEntityURI(sub=["culture", id])
                lobj.content = culture

                # Map the "Culture" classification
                lobj.classified_as = Type(
                    ident="http://vocab.getty.edu/aat/300055768", label="Culture"
                )

                # Map the "Brief Text" classification
                lobj.classified_as = Type(
                    ident="http://vocab.getty.edu/aat/300418049", label="Brief Text"
                )

                entity.referred_to_by = lobj

            cultures = self.loadCultures()
            if cultures:
                # Add a Type to the Object via its "classified_as" property that points to the AAT ID for the matched culture
                # where we can find an exact match; also add a "classified_as" to the Type of http://vocab.getty.edu/aat/300055768 (culture);
                # This allows us to convey both the literal string as well as (where known) the exact match for the AAT vocabulary term
                if culture in cultures:
                    info = cultures[culture]
                    if info:
                        type = Type()
                        type.id = info["id"]
                        type._label = info["label"]

                        # Map the "Culture" classification
                        type.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300055768",
                            label="Culture",
                        )

                        entity.classified_as = type

    # Map Object Material Statement (Medium)
    def mapMaterialStatement(self, entity, data):
        medium = get(data, "display.medium.display.value")
        if medium:
            id = get(data, "display.medium.uuid")
            if id:
                lobj = LinguisticObject()
                lobj.id = self.generateEntityURI(sub=["material-statement", id])
                lobj.content = medium

                # Map the “Materials Description" classification
                lobj.classified_as = Type(
                    ident="http://vocab.getty.edu/aat/300435429",
                    label="Materials Description",
                )

                # Map the "Brief Text" classification
                lobj.classified_as = Type(
                    ident="http://vocab.getty.edu/aat/300418049", label="Brief Text"
                )

                entity.referred_to_by = lobj

    # Map Object Materials (Medium)
    def mapMaterials(self, entity, data):
        medium = get(data, "display.medium.display.value")
        if medium:
            # Load our Materials mapping for the AAT Vocabulary
            materials = self.loadMaterials()
            if materials:
                # If the current medium string matches one of the defined and populated mappings
                if (medium in materials) and len(materials[medium]) > 0:
                    # Iterate through the mapped materials
                    for material in materials[medium]:
                        # debug(material, format="JSON")

                        # Then map them via Material entities to the Object via the "made_of" property
                        if has(material, "id") and has(material, "label"):
                            entity.made_of = Material(
                                ident=get(material, "id"), label=get(material, "label")
                            )

    # Map Object Inscriptions
    def mapInscriptions(self, entity, data):
        inscriptions = get(data, "display.marks.inscriptions")
        if inscriptions:
            # Add a LinguisticObject via the "carries" property on the Object
            # Add a classified_as to the LinguisticObject of Type http://vocab.getty.edu/aat/300028702 (inscriptions)
            for inscription in inscriptions:
                value = get(inscription, "display.value")
                if value:
                    id = get(inscription, "uuid")
                    if id:
                        lobj = LinguisticObject()
                        lobj.id = self.generateEntityURI(sub=["inscription", id])
                        lobj.content = value

                        # Map the "Inscription" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300028702",
                            label="Inscriptions",
                        )

                        # Map the “Inscription Description" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300435414",
                            label="Inscription Description",
                        )

                        # Map the "Brief Text" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300418049",
                            label="Brief Text",
                        )

                        entity.carries = lobj

    # Map Object Markings
    def mapMarkings(self, entity, data):
        markings = get(data, "display.marks.markings")
        if markings:
            # Add a LinguisticObject via the "carries" property on the Object
            # Add a classified_as to the LinguisticObject of Type http://vocab.getty.edu/aat/300028744 (marks (symbols))
            for marking in markings:
                value = get(marking, "display.value")
                if value:
                    id = get(marking, "uuid")
                    if id:
                        lobj = LinguisticObject()
                        lobj.id = self.generateEntityURI(sub=["mark", id])
                        lobj.content = value

                        # Map the "Marks (Symbols)" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300028744",
                            label="Marks (Symbols)",
                        )

                        # Map the “Marks Description" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300435420",
                            label="Marks Description",
                        )

                        # Map the "Brief Text" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300418049",
                            label="Brief Text",
                        )

                        entity.carries = lobj

    # Map Object Signatures
    def mapSignature(self, entity, data):
        signatures = get(data, "display.marks.signature")
        if signatures:
            # Add a LinguisticObject via the "carries" property on the Object
            # Add a classified_as to the LinguisticObject of Type http://vocab.getty.edu/aat/300028705 (signatures (names))
            for signature in signatures:
                value = get(signature, "display.value")
                if value:
                    id = get(signature, "uuid")
                    if id:
                        lobj = LinguisticObject()
                        lobj.id = self.generateEntityURI(sub=["signature", id])
                        lobj.content = value

                        # Map the “Signatures Description" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300435415",
                            label="Signatures Description",
                        )

                        # Map the "Brief Text" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300418049",
                            label="Brief Text",
                        )

                        entity.carries = lobj

    # Map Object Watermarks
    def mapWatermarks(self, entity, data):
        watermarks = get(data, "display.marks.watermarks")
        if watermarks:
            # Add a LinguisticObject via the "carries" property on the Object
            # Add a classified_as to the LinguisticObject of Type http://vocab.getty.edu/aat/300028749 (watermarks)
            for watermark in watermarks:
                value = get(watermark, "display.value")
                if value:
                    id = get(watermark, "uuid")
                    if id:
                        lobj = LinguisticObject()
                        lobj.id = self.generateEntityURI(sub=["watermark", id])
                        lobj.content = value

                        # Map the "Watermarks" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300028749",
                            label="Watermarks",
                        )

                        # Map the “Watermarks Description" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300435421",
                            label="Watermarks Description",
                        )

                        # Map the "Brief Text" classification
                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300418049",
                            label="Brief Text",
                        )

                        entity.carries = lobj

    # Map Object Place Created
    def mapPlaceCreated(self, entity, data):
        created = get(data, "display.places.created.display.value")
        if created:
            lobj = LinguisticObject()
            lobj.id = self.generateEntityURI(sub=["place", "created"])
            lobj._label = "Place Created"
            lobj.content = created

            lobj.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300435448",
                label="Creation Place Description",
            )

            lobj.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300418049", label="Brief Text"
            )

            entity.referred_to_by = lobj

    # Map Object Place Depicted
    def mapPlaceDepicted(self, entity, data):
        depicted = get(data, "display.places.depicted.display.value")
        if depicted:
            visual = VisualItem()
            visual.id = self.generateEntityURI(sub=["shows"])

            lobj = LinguisticObject()
            lobj.id = self.generateEntityURI(sub=["shows", "place", "depicted"])
            lobj._label = "Place Depicted"
            lobj.content = depicted

            lobj.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404655", label="Place Names"
            )
            lobj.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300418049", label="Brief Text"
            )
            lobj.classified_as = Type(
                ident="https://data.getty.edu/museum/ontology/linked-data/tms/object/place/depicted",
                label="Place Depicted",
            )

            visual.referred_to_by = lobj

            entity.shows = visual

    # Map Object Place Found
    def mapPlaceFound(self, entity, data):
        found = get(data, "display.places.found.display.value")
        if found:
            lobj = LinguisticObject()
            lobj.id = self.generateEntityURI(sub=["object", "place", "found"])
            lobj._label = "Place Found"
            lobj.content = found

            lobj.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404655", label="Place Names"
            )
            lobj.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300418049", label="Brief Text"
            )
            lobj.classified_as = Type(
                ident="https://data.getty.edu/museum/ontology/linked-data/tms/object/place/found",
                label="Place Found",
            )

            entity.referred_to_by = lobj

    # Map Object Main Image
    def mapMainImage(self, entity, data):
        image = get(data, "display.images.display")
        if image:
            derivative = None

            if has(image, "derivatives.larger"):
                derivative = get(image, "derivatives.larger")
            elif has(image, "derivatives.enlarge"):
                derivative = get(image, "derivatives.enlarge")
            elif has(image, "derivatives.thumbnail"):
                derivative = get(image, "derivatives.thumbnail")

            # debug(derivative, format="JSON")

            if derivative:
                derivativeURL = get(derivative, "url")
                if derivativeURL:
                    visual = VisualItem()

                    # Specify the image URL
                    visual.id = derivativeURL

                    # Specify the image view label
                    visual._label = get(image, "view", default="Main View")

                    # Specify the image MIME type format
                    visual.format = get(image, "mime")

                    # Map the "Digital Image" classification
                    visual.classified_as = Type(
                        ident="http://vocab.getty.edu/aat/300215302",
                        label="Digital Image",
                    )

                    # TODO How do we add InformationObjects to images? How do we define administrative attributes this way?
                    # info = InformationObject()
                    # info.id = "http://media.getty.edu/museum/images/web/larger/00094701.jpg/information/"
                    # info.content = "hello";
                    # visual.information = info

                    entity.representation = visual

    # Map Object Main Image IIIF
    def mapMainImageIIIF(self, entity, data):
        image = get(data, "display.images.display")
        if image:
            derivative = None

            if has(image, "iiif"):
                manifest = get(image, "iiif.manifest")
                profile = get(image, "iiif.profile")

            # TODO How do we add InformationObjects to images? How do we define administrative attributes this way?
            info = InformationObject()

            info.id = (
                "https://data.getty.edu/museum/api/iiif/"
                + get(data, "uuid")
                + "/manifest.json"
            )

            # Traceback (most recent call last):
            # File "//startup.py", line 63, in <module>
            # if(manager.processEntity(entity=options["entity"], id=options["id"], namespace=options["namespace"])):
            # File "/app/manager/__init__.py", line 60, in processEntity
            # if(entity.mapData()):
            # File "/app/transformers/__init__.py", line 425, in mapData
            # mapMethod(self.entity, self.data)
            # File "/app/transformers/museum/collection/ArtifactTransformer.py", line 430, in mapMainImageIIIF
            # info.conforms_to = Type(id="http://iiif.io/api/presentation")
            # File "/usr/local/lib/python3.7/site-packages/cromulent/model.py", line 505, in __setattr__
            # ok = self._check_prop(which, value)
            # File "/usr/local/lib/python3.7/site-packages/cromulent/model.py", line 543, in _check_prop
            # raise DataError("Can't set '%s' on resource of type '%s' to '%r'" % (which, self._type, value), self)
            # cromulent.model.DataError: Can't set 'conforms_to' on resource of type 'crm:E73_Information_Object' to '<cromulent.model.Type object at 0x7f58c6a76a20>'

            # cannot set InformationObject.conforms_to due to CROM error! CROM and/or Linked.art documentation are wrong!
            # info.conforms_to = Type(id="http://iiif.io/api/presentation")

            # Hack to get the "conforms_to" property into CROM's InformationObject instance data; attempting to set
            # the "conforms_to" property via direct assignment or via the setattr() method fails, as these assignments
            # are intercepted by CROM's __setattr__() method which rejects them; see DEV-1909 for more info; CROM needs fixing!
            info.__dict__["conforms_to"] = [{"id": "http://iiif.io/api/presentation"}]

            info.format = (
                'application/ld+json;profile="http://iiif.io/api/presentation/2/context.json"',
            )

            entity.subject_of = info

    # Map Alternate Images
    def mapAlternateImages(self, entity, data):
        pass

    # Map Object Home Page
    def mapHomePage(self, entity, data):
        id = get(data, "id")
        if id:
            # Web pages are referenced via LinguisticObject entities
            lobj = LinguisticObject()

            # Here we generate the full URL for the object homage page
            lobj.id = "http://www.getty.edu/art/collection/objects/" + str(id) + "/"
            lobj._label = "Homepage for Object"

            # Map the MIME type format for the referenced content
            lobj.format = "text/html"

            # Map the "Web Page" classification
            lobj.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300264578", label="Web Page"
            )

            # Map the "Primary" classification to note that this LinguisticObject references the canonical web page for the Object
            lobj.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404670", label="Primary"
            )

            entity.subject_of = lobj

    # Map Object Curatorial Department
    def mapCuratorialDepartment(self, entity, data):
        # For now add the Curatorial Department as a Group
        # that is a "member_of" the Group (organization) the J. Paul Getty Trust Musuem/Trust
        # and relate this to the Object entity via the "current_keeper" relationship.
        # This will need to be refactored later with a more accurate pattern that allows
        # for the Curatorial Department's oversight to be maintained even if the Object is on loan
        # and thus should temporarily have a different "current_keeper" assigned

        value = get(data, "display.department.display.value")
        if value:
            id = get(data, "display.department.uuid")
            if id:
                # Create a Group to represent the Curatorial Department
                group = Group()
                group.id = self.generateEntityURI(entity=Group, UUID=id)
                group._label = value + " (Curatorial Department)"

                # Map the "Department (Organizational Unit)" classification
                group.classified_as = Type(
                    ident="http://vocab.getty.edu/aat/300263534",
                    label="Department (Organizational Unit)",
                )

                # Map the Curatorial Department's name for the Group
                name = Name()
                name.id = self.generateEntityURI(entity=Group, UUID=id, sub=["name"])
                name.content = value

                group.identified_by = name

                # Map the Group to the Object's "current_keeper" property for now...
                entity.current_keeper = group

    # Map Object Current Owner
    def mapCurrentOwner(self, entity, data):
        # Get the Museum's Collection status for the Object
        status = get(data, "status")
        if status:
            # If the status is "PERMANENT COLLECTION"
            if status == "PERMANENT COLLECTION":
                # Note that the Object is currently owned by the J. Paul Getty Museum
                owner = self.createGettyMuseumGroup()
                if owner:
                    # Then assign the "current_owner" relationship for the Object
                    entity.current_owner = owner

    # Map Object Current Location
    def mapCurrentLocation(self, entity, data):
        # storage spaces = http://vocab.getty.edu/aat/300004465 (storage places)
        # gallery spaces = http://vocab.getty.edu/aat/300240057 (display places)

        location = get(data, "display.location")
        if location:
            id = get(data, "display.location.uuid")

            # Add Object's Current Location (Gallery/Storage)
            place = Place()
            place.id = self.generateEntityURI(entity=Place, UUID=id)
            place.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300240057",
                label="Galleries (Display Spaces) [Object On Display]",
            )
            place._label = "Gallery"

            # Obtain the Object's current location display value (name)
            value = get(
                location, "display.value"
            )  # e.g. "Getty Center, Museum West Pavilion, Gallery W204"
            if value:
                place._label = value

                name = Name()
                name.id = self.generateEntityURI(entity=Place, UUID=id, sub=["name"])
                name.content = value

                place.identified_by = name
        else:
            id = "a03fec3c-c7a2-4b29-9995-5eddf3ceb0a4"  # maps to the unknown storage location, perfect for the generic storage location concept

            place = Place()
            place.id = self.generateEntityURI(entity=Place, UUID=id)
            place.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300004465",
                label="Storage Spaces [Object Off Display]",
            )
            place._label = "Storage"

            name = Name()
            name.id = self.generateEntityURI(entity=Place, UUID=id, sub=["name"])
            name.content = "Storage"

            place.identified_by = name

        entity.current_location = place

    # Map Object Dimensions
    def mapDimensions(self, entity, data):
        dimensions = get(data, "display.dimensions")
        if dimensions:
            id = get(dimensions, "uuid")
            if id:
                # Add Object Dimensions Statement
                statement = get(dimensions, "display.value")
                if statement:
                    lobj = LinguisticObject()
                    lobj.id = self.generateEntityURI(sub=["dimensions", id])
                    lobj.content = statement

                    # Map the “Dimensions Description" classification
                    lobj.classified_as = Type(
                        ident="http://vocab.getty.edu/aat/300435430",
                        label="Dimensions Description",
                    )

                    # Map the "Brief Text" classification
                    lobj.classified_as = Type(
                        ident="http://vocab.getty.edu/aat/300418049", label="Brief Text"
                    )

                    entity.referred_to_by = lobj

                # Map any available dimensions measurements
                measurements = get(dimensions, "measurements")
                if measurements and len(measurements) > 0:
                    for measurement in measurements:
                        value = get(measurement, "display.value")
                        if value:
                            id = get(measurement, "uuid")
                            if id:
                                # Map the dimension value
                                dimension = Dimension()
                                dimension.id = self.generateEntityURI(
                                    sub=["dimension", id]
                                )
                                dimension.value = value

                                # Map the dimension measurement classification, e.g. Width
                                classification = get(measurement, "classification")
                                if classification:
                                    dimension.classified_as = Type(
                                        ident=get(classification, "id"),
                                        label=get(classification, "label"),
                                    )

                                # Map the dimension measurement unit classification, e.g. Centimeters
                                classification = get(measurement, "unit.classification")
                                if classification:
                                    dimension.unit = MeasurementUnit(
                                        ident=get(classification, "id"),
                                        label=get(classification, "label"),
                                    )

                                entity.dimension = dimension

    # Map Object Artist/Maker Relationship(s)
    def mapArtistMakerRelationships(self, entity, data):
        makers = get(data, "display.makers")
        if makers and len(makers) > 0:
            activities = []  # Store one or more Production activities temporarily...

            for maker in makers:
                # debug(maker, format="JSON")

                id = get(maker, "uuid")  # Maker UUID
                value = get(maker, "display.value")  # Maker name
                if id and value:
                    production = Production(  # Create the Production activity instance
                        ident=self.generateEntityURI(sub=["production", id]),
                        label="Production of Artwork",
                    )

                    # Artist/Maker Display Name (including any specified prefix and/or suffix and culture and dates)
                    name_display = get(maker, "display.value_combined")
                    if name_display:
                        lobj = LinguisticObject(
                            ident=self.generateEntityURI(
                                sub=["production", id, "producer-description"]
                            ),
                            label="Artist/Maker (Producer) Description",
                        )

                        lobj.content = name_display

                        lobj.classified_as = Type(
                            ident="https://data.getty.edu/museum/ontology/linked-data/tms/object/producer-description",
                            label="Producer Description",
                        )

                        lobj.classified_as = Type(
                            ident="http://vocab.getty.edu/aat/300418049",
                            label="Brief Text",
                        )

                        production.referred_to_by = lobj

                    person = Person(
                        ident=self.generateEntityURI(entity=Person, UUID=id),
                        label=value,
                    )

                    # Artist/Maker Artwork Production Role
                    role = get(maker, "role")
                    if role:
                        classification = get(role, "classification")
                        if classification and has(classification, "id"):
                            roleType = Type(
                                ident=get(classification, "id"),
                                label=get(classification, "label"),
                            )

                            roleType.classified_as = Type(
                                ident="http://vocab.getty.edu/aat/300435108",
                                label="Roles",
                            )

                            person.classified_as = roleType

                    # See https://linked.art/model/provenance/production.html#multiple-artists-with-roles
                    production.carried_out_by = person

                    # Artist/Maker Artwork Production Activity Dates
                    dates = get(maker, "dates")
                    if dates:
                        timespan = TimeSpan(
                            ident=self.generateEntityURI(
                                sub=["production", id, "timespan"]
                            ),
                            label="Production Dates",
                        )

                        display = get(dates, "display.value")
                        if display:
                            name = Name(
                                ident=self.generateEntityURI(
                                    sub=["production", id, "timespan", "name"]
                                ),
                                label="Production Dates",
                            )

                            name.content = display

                            timespan.identified_by = name

                        lower = get(dates, "value.lower")
                        if lower:
                            timespan.begin_of_the_begin = date(
                                format="%Y-%m-%dT%H:%M:%S",
                                date=lower,
                                format_for_input_date="%Y-%m-%d %H:%M:%S",
                            )

                        upper = get(dates, "value.upper")
                        if upper:
                            timespan.end_of_the_end = date(
                                format="%Y-%m-%dT%H:%M:%S",
                                date=upper,
                                format_for_input_date="%Y-%m-%d %H:%M:%S",
                            )

                        production.timespan = timespan

                    activities.append(production)

            production = None

            if len(activities) == 1 and activities[0]:
                production = activities[0]
            elif len(activities) > 1:
                production = Production(label="Production of Artwork",)

                for activity in activities:
                    production.part = activity

            if production:
                production.id = self.generateEntityURI(sub=["production"])

                # Object Creation Dates
                # Add via a TimeSpan on the `timespan` property of the Production activity
                dates = get(data, "display.date")
                if dates:
                    timespan = TimeSpan(
                        ident=self.generateEntityURI(sub=["production", "timespan"]),
                    )

                    # Add a Name to the TimeSpan of the Prodction activity to store the display date string
                    name = Name(
                        ident=self.generateEntityURI(
                            sub=["production", "timespan", "name"]
                        ),
                        label="Date",
                    )

                    name.content = get(dates, "display.value")

                    timespan.identified_by = name

                    # Get the padded lower and upper date values
                    lower = get(dates, "value.lower")
                    upper = get(dates, "value.upper")

                    if lower:
                        timespan.begin_of_the_begin = date(
                            format="%Y-%m-%dT%H:%M:%S",
                            date=lower,
                            format_for_input_date="%Y-%m-%d %H:%M:%S",
                        )

                    if upper:
                        timespan.end_of_the_end = date(
                            format="%Y-%m-%dT%H:%M:%S",
                            date=upper,
                            format_for_input_date="%Y-%m-%d %H:%M:%S",
                        )

                    # Associate the Production activity TimeSpan (this is overall timespan (dates) for the creation of the Object)
                    production.timespan = timespan

                entity.produced_by = production

    # Map Related Exhibitions
    def mapExhibitionRelationships(self, entity, data):
        exhibitions = get(data, "display.related.exhibitions")
        if exhibitions:
            for exhibition in exhibitions:
                venues = get(exhibition, "related.venues")
                if venues:
                    for venue in venues:
                        set = Set(
                            ident=self.generateEntityURI(
                                entity=Activity,
                                UUID=get(venue, "activity.uuid"),
                                sub=["objects"],
                            ),
                            label=sprintf("Objects exhibited in %s at %s" % (get(exhibition, "display.value"), get(venue, "display.value"))),
                        )

                        set.used_for = Activity(
                            ident=self.generateEntityURI(
                                entity=Activity,
                                UUID=get(venue, "activity.uuid"),
                            ),
                            label=sprintf("%s at %s" % (get(exhibition, "display.value"), get(venue, "display.value"))),
                        )

                        entity.member_of = set
