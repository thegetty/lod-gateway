from cromulent.model import factory, \
	Identifier, Mark, ManMadeObject as Object, Type, \
	Person, Material, MeasurementUnit, Place, Dimension, Currency, \
	ConceptualObject, TimeSpan, Actor, PhysicalThing, Language, \
	LinguisticObject, InformationObject, \
	Activity, Group, Name, MonetaryAmount, PropertyInterest, \
	Destruction, AttributeAssignment, BaseResource, PhysicalObject, \
	Acquisition, ManMadeFeature, VisualItem, Set, \
	PropositionalObject, Payment, Creation, Phase, Birth, Death, TimeSpan

from LAModelComponent import LAComponentType, LABaseComponent
from DOR_data_access import DORDataAccessPerson
from utilities import PrintToFile
import json

class LAModelPerson(LABaseComponent):
	def __init__(self):
		super().__init__()
		self.component_type = LAComponentType.Person
		self.dor_data_access = DORDataAccessPerson()
		
	def get_id_list(self):
		return [377, 378, 379, 380, 381, 382, 383, 384, 385, 386]

	def get_data(self, id):
		data = self.dor_data_access.get_data(id)
		return data

	def to_jsonld(self, data):

		# Entity
		p = Person(data["name"])

		# URI
		str_id = str(data["id"])
		p.id = self.base_uri_person + str_id
		p._label = data["name"]
	
		# Primary Name
		n = Name()
		n.id = p.id + "/name/1"
		n.content = data["name"]		

		t = Type()		
		t.id = "http://vocab.getty.edu/aat/300404670/"
		t._label = "Primary Name"
		n.classified_as = t
		p.identified_by = n

		# ULAN ID (if available)
		t = Type()
		t.id = "http://vocab.getty.edu/ulan/500115588-agent/"
		t._label = p._label
		p.exact_match = t

		# Birth Date
		b = Birth()
		b.id = p.id + "/activity/born"
		t = TimeSpan()

		t.id = p.id + "/time/born"
		t.begin_of_the_begin = data["date_began_year"]
		t.end_of_the_begin = data["date_began_year"]
		b.timespan = t

		# Birth Place modeled via took_place_at: E21Person (P98) was born - E67 Birth (P7) took place at: E53 Place
		# see http://www.cidoc-crm.org/Issue/ID-29-how-to-model-a-persons-birthplace
		pl = Place()
		
		pl.id = p.id + "place/born"
		pl._label = data["display_birthplace"]
		
		n = Name()
		n.id = p.id + "place/born/name"
		n.content = data["display_birthplace"]
		pl.identified_by = n
		
		t = Type()		
		t.id = "http://vocab.getty.edu/page/aat/300008347/"
		t._label = "Inhabited Place"
		pl.classified_as = t
		b.took_place_at = pl
		p.born = b

		# Death Date 
		d = Death()
		d.id = p.id + "activity/died"
		t = TimeSpan()
		t.id = p.id + "time/died"
		t.begin_of_the_end = data["date_ended_year"]
		t.end_of_the_end = data["date_ended_year"]
		d.timespan = t

		# Death Place modeled via took_place_at: E21Person (P100) was death of (died in) - E69 Death (P7) took place at: E53 Place
		# see http://www.cidoc-crm.org/Issue/ID-29-how-to-model-a-persons-birthplace
		pl = Place()
		pl.id = p.id + "place/died"
		pl._label = data["display_deathplace"]
		n = Name()
		n.id = p.id + "place/died/name"
		n.content = data["display_deathplace"]
		pl.identified_by = n
		t = Type()
		t.id = "http://vocab.getty.edu/page/aat/300008347/"
		t._label = "Inhabited Place"
		pl.classified_as = t
		d.took_place_at = pl
		p.died = d
		
		# Nationality
		t1 = Type()
		t1.id = "http://vocab.getty.edu/aat/300111175/"
		t1._label = data["display_nationality"]
		t2 = Type()
		t2.id = "http://vocab.getty.edu/aat/300379842/"
		t2._label = "Nationality"
		t1.classified_as = t2
		p.classified_as = t1

		# Biography
		l = LinguisticObject()
		l.id = p.id + "biography"
		l.id = p.id + "biography"
		l.content = "<p>Art was Van Gogh's means of personal, spiritual redemption, and his voluminous letters to his devoted brother Theo, offer profound insight into the artistic struggle.</p><p>Van Gogh became an artist in 1881. Although he studied briefly in Antwerp and Paris, he was largely self-taught. He ultimately chose to live in the country, and most of his paintings capture his deep affinity for nature. Theo, an art dealer, introduced Vincent to Paris's most advanced painters, and his work changed under the influences of Edgar Degas, Paul Gauguin, Georges Seurat, and Henri de Toulouse-Lautrec. The flatness of color and shape in Japanese <term>woodcuts</term> also inspired him.</p><p>Van Gogh's color expressed his emotions as he responded to the world. His insistence on color's expressive possibilities led him to develop a corresponding expressiveness in applying <term>pigment</term>. His brushstrokes of thick, opaque paint almost seem drawn. His often violently interacting colors and forms and strong expressive line influenced nearly every artistic movement that came after him: <term>Symbolism</term>, <term>Fauvism</term>, <term>Expressionism</term>, and beyond.</p>"
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300080102/"
		t._label = "Biography Statement"
		l.classified_as = t
		p.referred_to_by = l

		# Dump to a file
		result = factory.toString(p, compact=False)
		PrintToFile(str_id + "_Person.json"	, result)
