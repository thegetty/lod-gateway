from cromulent.model import factory, \
	Identifier, Mark, ManMadeObject as Object, Type, \
	Person, Material, MeasurementUnit, Place, Dimension, Currency, \
	ConceptualObject, TimeSpan, Actor, PhysicalThing, Language, \
	LinguisticObject, InformationObject, \
	Activity, Group, Name, MonetaryAmount, PropertyInterest, \
	Destruction, AttributeAssignment, BaseResource, PhysicalObject, \
	Acquisition, ManMadeFeature, VisualItem, Set, \
	PropositionalObject, Payment, Creation, Phase, Birth, Death, TimeSpan, Production, \
	PropositionalObject as Exhibition

from LAModelComponent import LAComponentType, LABaseComponent
from DOR_data_access import DORDataAccessObject
from utilities import PrintToFile, FindBetween
import json


class LAModelObject(LABaseComponent):
	def __init__(self):
		super().__init__()
		self.component_type = LAComponentType.Object
		self.dor_data_access = DORDataAccessObject()
		self.art_collection_uri = "http://www.getty.edu/art/collection/objects/"
		
	def get_id_list(self):
		#return [818, 819, 820, 821, 822, 823, 824, 825, 826, 827]
		return [826]

	def get_data(self, id):
		data = self.dor_data_access.get_data(id)
		return data

	def to_jsonld(self, data):
		# Entity
		o = Object(data["display_title"])

		# Set Object URI
		str_id = str(data["id"])
		o.id = self.base_uri_object + str_id
		
		# TODO Set Object Creation Date(s)

		# Set RightsStatements.org Assertion
		l = LinguisticObject()
		l.id = "http://rightsstatements.org/vocab/NoC-US/1.0/"
		l.content = "No Copyright - United States"
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300055547/"
		t._label = "Rights Statement"
		l.classified_as = t
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300418049/"
		t._label = "Brief Text"
		l.classified_as = t
		o.referred_to_by = l

		# Set Object Artist/Maker Relationship(s)
		a = Production()

		for maker in data["display_makers"]:
			a._label = "roduction of Artwork"
			p = Person(maker["display_value"])			
			p.id = self.base_uri_person + "activity/produced-by/" + str(maker["id"])
			a._label = "Production of Artwork"
			a.carried_out_by = p
			o.produced_by = a

		# Set Object Artwork Classification
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300133025/"
		t._label = "Artwork"
		o.classified_as = t

		# Set Object Painting Classification
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300033618/"
		t._label = data["display_classification"]
		o.classified_as = t

		# Set Object Accession Number
		i = Identifier()
		i.id = self.base_uri + "identifier/1/"
		i.content = data["display_number"]
		i._label = "Accession Number"

		# Set Object Accession Number Classification
		t = Type()
		t._label = "Accession Number"
		t.id = "http://vocab.getty.edu/aat/300312355/"
		i.classified_as = t
		o.identified_by = i

		# Set Object Primary Title & Set Primary Title Classification
		# This is important as it denotes the title as being the primary out of any titles associated with the work
		n = Name()
		n.id = self.base_uri_object + str_id + "/name/1/"
		n._label = "Primary Title"
		n.content = data["display_titles"]["primary_title"]["display_value"]
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300404670/"
		t._label = "Primary Title"
		n.classified_as = t
		o.identified_by = n

		# Add Object Alternate Title(s); in this case just one (as an example)		
		n = Name()
		n.id = self.base_uri_object + str_id + "/name/2/"
		n.content = data["name"]		
		n._label = "Example Secondary Title"
		o.identified_by = n

		# Add Object Dimensions
		# Add Object Width
		d = Dimension()
		d.id = self.base_uri_object + str_id + "/dimension/1/"
		dim = data["display_dimensions"]
		dim = FindBetween(dim, "(", ")").replace('in.', '').strip().split('×')
		d.value = dim[0].strip()
		m = MeasurementUnit()
		m.id = "http://vocab.getty.edu/aat/300379100/"
		m._label = "inches"
		d.unit = m
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300055647/"
		t._label = "Width"
		d.classified_as = t
		o.dimension = d

		# Add Object Height
		d = Dimension()
		d.id = self.base_uri_object + d.id + "dimension/2/"
		d.value = dim[1].strip()
		m = MeasurementUnit()
		m.id = "http://vocab.getty.edu/aat/300379100/"
		m._label = "inches"
		d.unit = m
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300055644/"
		t._label = "Height"
		d.classified_as = t
		o.dimension = d

		# Add Object Dimensions Statement
		l = LinguisticObject()
		l.id = self.base_uri_object + str_id + "dimension-statement/"
		l.content = data["display_dimensions"]
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300266036/"
		t._label = "Dimension Statement"
		l.classified_as = t
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300418049/"
		t._label = "Brief Text"
		l.classified_as = t
		o.referred_to_by = l

		# Add Object Materials
		m = Material()
		m.id = "http://vocab.getty.edu/aat/300015050/"
		m._label = "oil paint (paint)"
		o.made_of = m

		m = Material()
		m.id = "http://vocab.getty.edu/aat/300014078/"
		m._label = "canvas (textile material)"
		o.made_of = m

		# Add Object Material Description
		l = LinguisticObject()
		l.id = self.base_uri_object + str_id + "material-statement/"
		l.content = data["display_medium"]
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300010358/"
		t._label = "Material Statement"
		l.classified_as = t
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300418049/"
		t._label = "Brief Text"
		l.classified_as = t
		o.referred_to_by = l

		# Add Object Description
		l = LinguisticObject()
		l.id = self.base_uri_object + str_id + "description/"
		l.content = data["display_description"]		
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300080091/"
		t._label = "Description"
		l.classified_as = t
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300418049/"
		t._label = "Brief Text"
		l.classified_as = t
		o.referred_to_by = l

		# Add Object Culture Description
		l = LinguisticObject()
		l.id = self.base_uri_object + str_id + "culture-statement"
		l.content = data["display_culture"]
		t = Type()
		t.id = "http://vocab.getty.edu/page/aat/300055768"
		t._label = "Culture Statement"
		l.classified_as = t
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300418049/"
		t._label = "Brief Text"
		l.classified_as = t
		o.referred_to_by = l

		# Add Object Shows (VisualItem)
		v = VisualItem()
		v.id = self.base_uri_object + str_id + "shows/1/"		
		pl = Place()
		pl.id = self.base_uri_object + str_id + "place/created"
		pl._label = data["display_place_created"]
		n = Name()
		n.id = "https://data.getty.edu/museum/collection/object/826/place/created/name/"
		n.content = data["display_place_created"]		
		pl.identified_by = n
		t = Type()
		t.id = "http://vocab.getty.edu/page/aat/300008347/"
		t._label = "Inhabited Place"
		pl.classified_as = t
		v.represents = pl
		o.shows = v

		# Add Object Main Image
		v = VisualItem()
		v.id = data["display_image"]["image_larger"]["resource_uri"]		
		v._label = "Main Image"
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300215302/"
		t._label = "Digital Image"
		v.classified_as = t
		v.format = "image/jpeg"
		o.representation = v

		# Add Object Home Page
		l = LinguisticObject()
		l.id = self.art_collection_uri + str_id
		l._label = "Homepage for Object"
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300264578/"
		t._label = "Web Page"
		l.classified_as = t
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300404670/"
		t._label = "Primary"
		l.classified_as = t
		l.format = "text/html"
		o.subject_of = l

		# Add Object's Current Location (Gallery/Storage)
		pl = Place()
		pl.id = "https://data.getty.edu/museum/collection/place/279/getty-center-west-pavilion-gallery-204/"
		pl._label = data["display_location"]
		
		n = Name()
		n.id = "https://data.getty.edu/museum/collection/place/279/getty-center-west-pavilion-gallery-204/name/"
		n.content = data["display_location"]

		pl.identified_by = n
		o.current_location = pl

		# Add Ownership
		g = Group()
		g.id = "http://vocab.getty.edu/ulan/500115988/"
		g._label = "J. Paul Getty Museum, Los Angeles, California"
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300312281/"
		t._label = "Museum"
		g.classified_as = t
		a = Acquisition()
		a.id = self.base_uri_object + str_id + "activity/acqusition/"		
		a._label = "Acquisition"
		g.acquired_title_through = a
		o.current_owner = g


		# TODO Add Previous Ownership (Provenance)


		# Add Exhibition History
		e = Exhibition()
		e.id = "https://data.getty.edu/museum/collection/exhibition/999/"
		e._label = "Salon des Indépendants"

		i = Identifier()
		i.id = "https://data.getty.edu/museum/collection/exhibition/999/identifier/1/"
		i._label = "Exhibition Name"
		e.identified_by = i

		n = Name()
		n.id = "https://data.getty.edu/museum/collection/exhibition/999/name/"
		n.content = "Salon des Indépendants"
		e.identified_by = n

		t = Type()
		t.id = "http://vocab.getty.edu/aat/300417531/"
		t._label = "Exhibition"
		e.classified_as = t

		e.about = []

		ea = Activity()
		ea.id = "https://data.getty.edu/museum/collection/exhibition/999/activity/"
		ea._label = "Exhibition Activity"
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300054766/"
		t._label = "Exhibiting"
		ea.classified_as = t

		e.motivated = ea

		c = Creation()
		c.id = "https://data.getty.edu/museum/collection/exhibition/999/creation/"
		c._label = "Creation"

		cp = Person()
		cp.id = "https://data.getty.edu/museum/collection/person/x/"
		cp._label = "Curator"
		c.carried_out_by = cp

		e.created_by = c

		a = Activity()
		a.id = "https://data.getty.edu/museum/collection/exhibition/999/activity/"
		a._label = "Salon des Indépendants"

		a.timespan = TimeSpan()
		a.timespan.id = "https://data.getty.edu/museum/collection/exhibition/999/time-span/"
		a.timespan.begin_of_the_begin = ""
		a.timespan.end_of_the_end = ""
		g = Group()
		g.id = "https://data.getty.edu/museum/collection/group/x/"
		g._label = "X"
		t = Type()
		t.id = "http://vocab.getty.edu/aat/300312281/"
		t._label = "Museum"
		g.classified_as = t
		a.carried_out_by = g

		# TODO How do we associate exhibitions with the Object?

		# added by V. to produce files
		result = factory.toString(o, compact=False)
		PrintToFile(str_id + "_Object.json"	, result)


