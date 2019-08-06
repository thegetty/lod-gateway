# Import our application utility functions
from app.utilities import get, has, debug

# Import our Museum Collection BaseTransformer class
from app.transformers.museum.collection.BaseTransformer import BaseTransformer

# Import the cromulent model for handling the assembly and export of our linked data
from cromulent.model import factory, \
	Identifier, Mark, HumanMadeObject as Object, Type, \
	Person, Material, MeasurementUnit, Place, Dimension, Currency, \
	ConceptualObject, TimeSpan, Actor, PhysicalThing, Language, \
	LinguisticObject, InformationObject, \
	Activity, Group, Name, MonetaryAmount, PropertyInterest, \
	Destruction, AttributeAssignment, BaseResource, PhysicalObject, \
	Acquisition, HumanMadeFeature, VisualItem, Set, \
	PropositionalObject, Payment, Creation, Phase, Birth, Death, TimeSpan, Production, \
	PropositionalObject as Exhibition

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
	
	def mapEntity(self, entity, data):
		pass
	
	def mapID(self, entity, data):
		pass
	
	def mapName(self, entity, data):
		pass
	
	def mapPavilion(self, entity, data):
		pass
	
	def mapBuilding(self, entity, data):
		pass
	
	def mapFloor(self, entity, data):
		pass
	
	def mapRoom(self, entity, data):
		pass
