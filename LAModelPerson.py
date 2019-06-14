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
		return [377, 378]

	def get_data(self, id):
		data = self.dor_data_access.get_data(id)
		return data

	def to_jsonld(self, data):

		# Define Person Entity
		p = Person("Van Gogh")
		# Set Person URI
		p.id = "https://data.getty.edu/museum/collection/person/377/"
		p._label = "Vincent van Gogh"
	
		# Add Person Primary Name
		n = Name()
		n.id = "https://data.getty.edu/museum/collection/person/377/name/1/"
		n.content = "Vincent van Gogh"
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300404670/"
		t._label = "Primary Name"
		n.classified_as = t
		p.identified_by = n

		# Add Person ULAN ID (if available)
		t = Type()
		t.id = "http://vocab.getty.edu/ulan/500115588-agent/"
		t._label = "Vincent van Gogh"
		p.exact_match = t

		# Add Person Birth Date (Vincent van Gogh; Born 1853 in Zundert, The Netherlands)
		b = Birth()
		b.id = "https://data.getty.edu/museum/collection/person/377/activity/born/"
		t = TimeSpan()
		t.id = "https://data.getty.edu/museum/collection/person/377/time/born/"
		t.begin_of_the_begin = "1853"
		t.end_of_the_begin = "1853"
		b.timespan = t
		# Birth Place modeled via took_place_at: E21Person (P98) was born - E67 Birth (P7) took place at: E53 Place
		# see http://www.cidoc-crm.org/Issue/ID-29-how-to-model-a-persons-birthplace
		pl = Place()
		pl.id = "https://data.getty.edu/museum/collection/person/377/place/born/"
		pl._label = "Zundert, The Netherlands"
		n = Name()
		n.id = "https://data.getty.edu/museum/collection/person/377/place/born/name/"
		n.content = "Zundert, The Netherlands"
		pl.identified_by = n
		t = Type()
		t.id = "http://vocab.getty.edu/page/aat/300008347/"
		t._label = "Inhabited Place"
		pl.classified_as = t
		b.took_place_at = pl
		p.born = b

		# print(dir(b))

		# Add Person Death Date (Vincent van Gogh; Died 1899 in Auvers-sur-Oise, France)
		d = Death()
		d.id = "https://data.getty.edu/museum/collection/person/377/activity/died/"
		t = TimeSpan()
		t.id = "https://data.getty.edu/museum/collection/person/377/time/died/"
		t.begin_of_the_end = "1890"
		t.end_of_the_end = "1890"
		d.timespan = t
		# Death Place modeled via took_place_at: E21Person (P100) was death of (died in) - E69 Death (P7) took place at: E53 Place
		# see http://www.cidoc-crm.org/Issue/ID-29-how-to-model-a-persons-birthplace
		pl = Place()
		pl.id = "https://data.getty.edu/museum/collection/person/377/place/died/"
		pl._label = "Auvers-sur-Oise, France"
		n = Name()
		n.id = "https://data.getty.edu/museum/collection/person/377/place/died/name/"
		n.content = "Auvers-sur-Oise, France"
		pl.identified_by = n
		t = Type()
		t.id = "http://vocab.getty.edu/page/aat/300008347/"
		t._label = "Inhabited Place"
		pl.classified_as = t
		d.took_place_at = pl
		p.died = d

		# Add Person Activity Start Date (if known)
		# a = Activity()
		# a.id = "https://data.getty.edu/museum/collection/activity/377/active/from/"
		# p.carried_out = a

		# Add Person Activity End Date (if known)
		# a = Activity()
		# a.id = "https://data.getty.edu/museum/collection/activity/377/active/to/"
		# p.carried_out = a

		# Add Person Nationality
		t1 = Type()
		t1.id = "http://vocab.getty.edu/aat/300111175/"
		t1._label = "Dutch"
		t2 = Type()
		t2.id = "http://vocab.getty.edu/aat/300379842/"
		t2._label = "Nationality"
		t1.classified_as = t2
		p.classified_as = t1

		# Add Person Biography
		l = LinguisticObject()
		l.id = "https://data.getty.edu/museum/collection/person/377/biography/"
		l.content = "<p>Art was Van Gogh's means of personal, spiritual redemption, and his voluminous letters to his devoted brother Theo, offer profound insight into the artistic struggle.</p><p>Van Gogh became an artist in 1881. Although he studied briefly in Antwerp and Paris, he was largely self-taught. He ultimately chose to live in the country, and most of his paintings capture his deep affinity for nature. Theo, an art dealer, introduced Vincent to Paris's most advanced painters, and his work changed under the influences of Edgar Degas, Paul Gauguin, Georges Seurat, and Henri de Toulouse-Lautrec. The flatness of color and shape in Japanese <term>woodcuts</term> also inspired him.</p><p>Van Gogh's color expressed his emotions as he responded to the world. His insistence on color's expressive possibilities led him to develop a corresponding expressiveness in applying <term>pigment</term>. His brushstrokes of thick, opaque paint almost seem drawn. His often violently interacting colors and forms and strong expressive line influenced nearly every artistic movement that came after him: <term>Symbolism</term>, <term>Fauvism</term>, <term>Expressionism</term>, and beyond.</p>"
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300080102/"
		t._label = "Biography Statement"
		l.classified_as = t
		p.referred_to_by = l

		# added by V. to produce files
		result = factory.toString(p, compact=False)
		f_name = str(data["id"])
		PrintToFile(f_name + "_Person.jaon"	, result)
