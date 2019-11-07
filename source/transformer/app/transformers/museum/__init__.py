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
		JPGM = Group()
		
		# The UUID c496a7b4-6087-4deb-a1ac-0f21bd3fd87b corresponds to the J. Paul Getty Museum TMS/DOR Constituent
		JPGM.id = self.generateEntityURI(entity=Group, id="c496a7b4-6087-4deb-a1ac-0f21bd3fd87b")
		
		JPGM._label = "J. Paul Getty Museum, Los Angeles, California"
		
		# Return a copy of the Group so it can be modified without affecting the source
		return copy.copy(JPGM)
