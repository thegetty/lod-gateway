from . BaseRecord import BaseRecord

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

from ..... utilities import get, has, debug

class GalleryRecord(BaseRecord):
	
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
