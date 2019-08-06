import copy

# Import our shared transformers BaseTransformer class
from app.transformers import BaseTransformer as SharedBaseTransformer

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

class BaseTransformer(SharedBaseTransformer):
	
	# Create J. Paul Getty Museum Group Entity
	def createGettyMuseumGroup(self):
		JPGT = self.createGettyTrustGroup()
		
		JPGM = Group()
		JPGM.id = "http://vocab.getty.edu/ulan/500115988"
		JPGM._label = "J. Paul Getty Museum, Los Angeles, California"
		JPGM.classified_as = Type(ident="http://vocab.getty.edu/aat/300312281", label="Museum")
		
		# Note that the Museum is a "member_of" (part of) the Trust
		JPGM.member_of = JPGT
		
		# Return a copy of the Group so it can be modified without affecting the source
		return copy.copy(JPGM)
