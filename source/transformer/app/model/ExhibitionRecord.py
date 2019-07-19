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

from .. utilities import get, has, debug

class ExhibitionRecord(BaseRecord):
	
	def resourceType(self):
		return "exhibition"
	
	def entityType(self):
		return Exhibition
	
	def mapEntity(self, entity, data):
		pass