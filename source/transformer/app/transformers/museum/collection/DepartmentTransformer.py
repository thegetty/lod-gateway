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


class DepartmentTransformer(BaseTransformer):
    def activityStreamObjectTypes(self):
        """Provide a method for conveying the supported Activity Stream Object type names that this transformer will handle"""
        return [
            "Department",
        ]

    def resourceType(self):
        return "department"

    def entityType(self):
        return Group

    # Map the "Department (Organizational Unit)" Classification
    def mapClassification(self, entity, data):
        entity.classified_as = Type(
            ident="http://vocab.getty.edu/aat/300263534",
            label="Department (Organizational Unit)",
        )

    # Map the Curatorial Department's Name for the Group
    def mapName(self, entity, data):
        id = get(data, "uuid")
        value = get(data, "display.name")
        if id and value:
            name = Name(
                ident=self.generateEntityURI(UUID=id, sub=["name"]),
                label="Curatorial Department Name",
            )

            name.content = value

            entity.identified_by = name

    # Map the Curatorial Department's Parent Group
    def mapParent(self, entity, data):
        entity.member_of = self.createGettyMuseumGroup()
