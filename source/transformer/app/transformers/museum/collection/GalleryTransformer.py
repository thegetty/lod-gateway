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


class GalleryTransformer(BaseTransformer):
    def activityStreamObjectTypes(self):
        """Provide a method for conveying the supported Activity Stream Object type names that this transformer will handle"""
        return ["Gallery"]

    def resourceType(self):
        return "gallery"

    def entityType(self):
        return Place

    def mapClassification(self, entity, data):
        entity.classified_as = Type(
            ident="http://vocab.getty.edu/aat/300240057",
            label="Galleries (Display Spaces)",
        )

    def mapName(self, entity, data):
        content = get(data, "display_name")
        if content:
            name = Name(
                ident=self.generateEntityURI(sub=["gallery", "name"]),
                label="Gallery Name",
            )

            name.content = content

            name.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Names"
            )

            name.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404688",
                label="Full Names (Personal Names)",
            )

            entity.identified_by = name

    def mapPavilion(self, entity, data):
        content = get(data, "pavilion")
        if content:
            identifier = Identifier(
                ident=self.generateEntityURI(sub=["pavilion", "mnemonic"]),
                label="Pavilion Mnemonic",
            )

            identifier.content = content

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Names"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300263127", label="Mnemonic"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300002660", label="Pavilion"
            )

            entity.identified_by = identifier

    def mapPavilionName(self, entity, data):
        content = get(data, "display_pavilion")
        if content:
            identifier = Identifier(
                ident=self.generateEntityURI(sub=["pavilion", "name"]),
                label="Pavilion Name",
            )

            identifier.content = content

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Names"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300002660", label="Pavilion"
            )

            entity.identified_by = identifier

    def mapBuilding(self, entity, data):
        content = get(data, "building")
        if content:
            identifier = Identifier(
                ident=self.generateEntityURI(sub=["building", "mnemonic"]),
                label="Building Mnemonic",
            )

            identifier.content = content

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Names"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300263127", label="Mnemonic"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300004792", label="Building"
            )

            entity.identified_by = identifier

    def mapBuildingName(self, entity, data):
        content = get(data, "display_building")
        if content:
            identifier = Identifier(
                ident=self.generateEntityURI(sub=["building", "name"]),
                label="Building Name",
            )

            identifier.content = content

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Names"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300004792", label="Building"
            )

            entity.identified_by = identifier

    def mapFloor(self, entity, data):
        content = get(data, "floor")
        if content:
            identifier = Identifier(
                ident=self.generateEntityURI(sub=["floor", "id"]), label="Floor ID"
            )

            identifier.content = content

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Names"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300002060",
                label="Floors (Surface Elements)",
            )

            entity.identified_by = identifier

    def mapFloorName(self, entity, data):
        content = get(data, "display_floor")
        if content:
            identifier = Identifier(
                ident=self.generateEntityURI(sub=["floor", "name"]), label="Floor Name"
            )

            identifier.content = content

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Names"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300002060",
                label="Floors (Surface Elements)",
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404670", label="Preferred Term"
            )

            entity.identified_by = identifier

    def mapRoom(self, entity, data):
        content = get(data, "room")
        if content:
            identifier = Identifier(
                ident=self.generateEntityURI(sub=["room", "mnemonic"]),
                label="Room Mnemonic",
            )

            identifier.content = content

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Names"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300263127", label="Mnemonic"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300133704", label="Rooms and Spaces"
            )

            entity.identified_by = identifier

    def mapRoomName(self, entity, data):
        content = get(data, "display_room")
        if content:
            identifier = Identifier(
                ident=self.generateEntityURI(sub=["room", "name"]), label="Room Name"
            )

            identifier.content = content

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Names"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300133704", label="Rooms and Spaces"
            )

            entity.identified_by = identifier

    def mapSite(self, entity, data):
        content = get(data, "site")
        if content:
            identifier = Identifier(
                ident=self.generateEntityURI(sub=["site", "mnemonic"]),
                label="Site Mnemonic",
            )

            identifier.content = content

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Names"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300263127", label="Mnemonic"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300000809", label="Sites (Locations)"
            )

            entity.identified_by = identifier

    def mapSiteName(self, entity, data):
        content = get(data, "display_site")
        if content:
            identifier = Identifier(
                ident=self.generateEntityURI(sub=["site", "name"]), label="Site Name"
            )

            identifier.content = content

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300404650", label="Names"
            )

            identifier.classified_as = Type(
                ident="http://vocab.getty.edu/aat/300000809", label="Sites (Locations)"
            )

            entity.identified_by = identifier
