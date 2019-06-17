from cromulent.model import factory, \
	Identifier, Mark, ManMadeObject as Object, Type, \
	Person, Material, MeasurementUnit, Place, Dimension, Currency, \
	ConceptualObject, TimeSpan, Actor, PhysicalThing, Language, \
	LinguisticObject, InformationObject, \
	Activity, Group, Name, MonetaryAmount, PropertyInterest, \
	Destruction, AttributeAssignment, BaseResource, PhysicalObject, \
	Acquisition, ManMadeFeature, VisualItem, Set, \
	PropositionalObject, Payment, Creation, Phase, Birth, Death, TimeSpan

import json
from DOR_data_access import DORDataAccess
from utilities import PrintToFile
from abc import ABC, abstractmethod
from enum import Enum


# Linked Art Models used in MART
class LAComponentType(Enum):
    Object     = 1
    Person     = 2
    Group      = 3
    Provenance = 4
    Place      = 5
    Collection = 6


# Abstract base class for all LA Model Components.
class LABaseComponent(ABC):
    def __init__(self):
        self.component_type  = None
        self.dor_data_access = None
        self.id_list         = None
        self.base_uri        = "https://data.getty.edu/museum/collection"
        self.base_uri_object = "https://data.getty.edu/museum/collection/object/"
        self.base_uri_person = "https://data.getty.edu/museum/collection/person/"

    @abstractmethod
    def get_id_list(self):
        pass

    @abstractmethod
    def get_data(self, id):
        pass

    @abstractmethod
    def to_jsonld(self, data):
        pass



