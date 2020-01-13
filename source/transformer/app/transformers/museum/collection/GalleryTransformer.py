# Import our application utility functions
from app.utilities import get, has, debug

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


class GalleryTransformer(BaseTransformer):
    def activityStreamObjectTypes(self):
        """Provide a method for conveying the supported Activity Stream Object type names that this transformer will handle"""
        return [
            "Gallery",
        ]

    def resourceType(self):
        return "gallery"

    def entityType(self):
        return Place

    # final method; please do not override
    def assembleHeaders(self):
        """Assemble our HTTP Request Headers for the DOR API call"""

        headers = super().assembleHeaders()

        # Ask the DOR to respond with Gallery metadata structured hierarchically,
        # rather than the 'flattened' structure provided usually; this ensures that
        # the structuring and additional metadata attributes needed to assemble the
        # LOD Gallery records is made available for use below.
        headers["Accept"] += ";schema=HIERARCHICAL"

        return headers

    def mapClassification(self, entity, data):
        subtype = get(data, "subtype")
        if subtype == "GALLERY":
            entity.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300240057",
                label="Galleries (Display Spaces)",
            )
        elif subtype == "PAVILION":
            entity.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300002660",
                label="Pavilion (Subsidiary Buildings)",
            )
        elif subtype == "BUILDING":
            entity.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300004792",
                label="Buildings (Structures)",
            )
        elif subtype == "SITE":
            entity.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300000809", label="Sites (Locations)",
            )

    def mapName(self, entity, data):
        content = get(data, "display.value")
        if content:
            entity._label = content

            name = Name(
                ident=self.generateEntityURI(sub=["gallery-name"]),
                label="Gallery Name",
            )

            name.content = content

            name.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404688",
                label="Full Names (Personal Names)",
            )

            name.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Preferred Term"
            )

            entity.identified_by = name

    def mapPavilion(self, entity, data):
        content = get(data, "pavilion")
        if content:
            name = Name(
                ident=self.generateEntityURI(sub=["pavilion-mnemonic"]),
                label="Pavilion Mnemonic",
            )

            name.content = content

            name.classified_as = Type(
                ident="https://data.getty.edu/museum/ontology/linked-data/tms/pavilion-mnemonic",
                label="Pavilion Mnemonic",
            )

            entity.identified_by = name

    def mapPavilionName(self, entity, data):
        content = get(data, "display.pavilion")
        if content:
            name = Name(
                ident=self.generateEntityURI(sub=["pavilion-name"]),
                label="Pavilion Name",
            )

            name.content = content

            name.classified_as = Type(
                ident="https://data.getty.edu/museum/ontology/linked-data/tms/pavilion-name",
                label="Pavilion Name",
            )

            entity.identified_by = name

    def mapBuilding(self, entity, data):
        content = get(data, "building")
        if content:
            name = Name(
                ident=self.generateEntityURI(sub=["building-mnemonic"]),
                label="Building Mnemonic",
            )

            name.content = content

            name.classified_as = Type(
                ident="https://data.getty.edu/museum/ontology/linked-data/tms/building-mnemonic",
                label="Building Mnemonic",
            )

            entity.identified_by = name

    def mapBuildingName(self, entity, data):
        content = get(data, "display.building")
        if content:
            name = Name(
                ident=self.generateEntityURI(sub=["building-name"]),
                label="Building Name",
            )

            name.content = content

            name.classified_as = Type(
                ident="https://data.getty.edu/museum/ontology/linked-data/tms/building-name",
                label="Building Name",
            )

            entity.identified_by = name

    def mapFloor(self, entity, data):
        content = get(data, "floor")
        if content:
            name = Name(
                ident=self.generateEntityURI(sub=["floor-mnemonic"]),
                label="Floor Mnemonic",
            )

            name.content = content

            name.classified_as = Type(
                ident="https://data.getty.edu/museum/ontology/linked-data/tms/floor-mnemonic",
                label="Floor Mnemonic",
            )

            entity.identified_by = name

    def mapFloorName(self, entity, data):
        content = get(data, "display.floor")
        if content:
            name = Name(
                ident=self.generateEntityURI(sub=["floor-name"]), label="Floor Name"
            )

            name.content = content

            name.classified_as = Type(
                ident="https://data.getty.edu/museum/ontology/linked-data/tms/floor-name",
                label="Floor Name",
            )

            entity.identified_by = name

    def mapRoom(self, entity, data):
        content = get(data, "room")
        if content:
            name = Name(
                ident=self.generateEntityURI(sub=["room-mnemonic"]),
                label="Room Mnemonic",
            )

            name.content = content

            name.classified_as = Type(
                ident="https://data.getty.edu/museum/ontology/linked-data/tms/room-mnemonic",
                label="Room Mnemonic",
            )

            entity.identified_by = name

    def mapRoomName(self, entity, data):
        content = get(data, "display.room")
        if content:
            name = Name(
                ident=self.generateEntityURI(sub=["room-name"]), label="Room Name"
            )

            name.content = content

            name.classified_as = Type(
                ident="https://data.getty.edu/museum/ontology/linked-data/tms/room-name",
                label="Room Name",
            )

            entity.identified_by = name

    # Map Gallery's Ancestor Places (if any)
    def mapAncestors(self, entity, data):
        # Map Gallery Parent Helper Method
        def mapParent(entity, parent):
            if parent:
                entity.part_of = place = Place(
                    ident=self.generateEntityURI(UUID=get(parent, "uuid")),
                    label=get(parent, "display.value"),
                )

                # Map the current Place's Parent (if any) recursively
                mapParent(place, get(parent, "parent"))

        # Map the current Place's parent/ancestors (if any) recursively
        mapParent(entity, get(data, "parent"))

    # Map Gallery's Child Places (if any)
    def mapChildren(self, entity, data):
        children = get(data, "children")
        if children and len(children) > 0:
            for child in children:
                # Place.part maps to crm:P89i_contains
                entity.part = Place(
                    ident=self.generateEntityURI(UUID=get(child, "uuid")),
                    label=get(child, "display.value"),
                )
