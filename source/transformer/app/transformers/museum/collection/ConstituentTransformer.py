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

class ConstituentTransformer(BaseTransformer):
	
	def activityStreamObjectTypes(self):
		"""Provide a method for conveying the supported Activity Stream Object type names that this transformer will handle"""
		return [
			"Constituent",
		]
	
	def resourceType(self):
		return "constituent"
	
	def entityType(self):
		if(self.data):
			if(self.data["type"]):
				if(self.data["type"] == "INDIVIDUAL"):
					return Person
				else:
					return Group
			else:
				raise RuntimeError("Missing Source Data 'type' Attribute!")
		else:
			raise RuntimeError("Missing Source Data!")
		
		return None
	
	# Map Primary Name
	def mapPrimaryName(self, entity, data):
		value = get(data, "display.name.display.value")
		if(value):
			name = Name()
			name.id = self.generateEntityURI(sub=["name"])
			name.content = value
			
			name.classified_as = Type(ident="http://vocab.getty.edu/aat/300404670", label="Primary Name")
			
			entity.identified_by = name
	
	# Map Alternate Names
	def mapAlternateNames(self, entity, data):
		pass
	
	# Map Identifiers
	def mapIdentifiers(self, entity, data):
		identifiers = get(data, "display.identifiers")
		if(identifiers and len(identifiers) > 0):
			for identifier in identifiers:
				
				# Add ULAN ID (if available)
				if(get(identifier, "name") == "ULAN ID"):
					if(has(identifier, "classification.id")):
						type = Type()
						type.id = get(identifier, "classification.id")
						type._label = get(identifier, "classification.label")
						
						entity.exact_match = type
	
	# Map Roles
	def mapRoles(self, entity, data):
		pass
	
	# Map Birth Place/Time
	def mapBirthPlace(self, entity, data):
		if(get(data, "type") == "INDIVIDUAL"):
			if(has(data, "display.places.birth")):
				birth = Birth()
				birth.id = self.generateEntityURI(sub=["birth", "activity"])
				
				date = get(data, "display.places.birth.date.iso")
				if(date):
					timespan = TimeSpan()
					timespan.id = self.generateEntityURI(sub=["birth", "timespan"])
					timespan.begin_of_the_begin = date
					timespan.end_of_the_begin   = date
					birth.timespan = timespan
				
				value = get(data, "display.places.birth.display.value")
				if(value):
					# Birth Place modeled via took_place_at: E21Person (P98) was born - E67 Birth (P7) took place at: E53 Place
					# See http://www.cidoc-crm.org/Issue/ID-29-how-to-model-a-persons-birthplace
					place = Place()
					place.id = self.generateEntityURI(sub=["birth", "place"])
					place._label = value
					
					name = Name()
					name.id = self.generateEntityURI(sub=["birth", "place", "name"])
					name.content = value
					place.identified_by = name
					
					birth.took_place_at = place
					
					entity.born = birth
	
	# Map Death Place/Time
	def mapDeathPlace(self, entity, data):
		if(get(data, "type") == "INDIVIDUAL"):
			if(has(data, "display.places.death")):
				death = Death()
				death.id = self.generateEntityURI(sub=["death", "activity"])
				
				date = get(data, "display.places.death.date.iso")
				if(date):
					timespan = TimeSpan()
					timespan.id = self.generateEntityURI(sub=["death", "timespan"])
					timespan.begin_of_the_begin = date
					timespan.end_of_the_begin   = date
					death.timespan = timespan
				
				value = get(data, "display.places.death.display.value")
				if(value):
					# Death Place modeled via took_place_at: E21Person (P100) was death of (died in) - E69 Death (P7) took place at: E53 Place
					# See http://www.cidoc-crm.org/Issue/ID-29-how-to-model-a-persons-birthplace for concepts
					place = Place()
					place.id = self.generateEntityURI(sub=["death", "place"])
					place._label = value
					
					name = Name()
					name.id = self.generateEntityURI(sub=["death", "place", "name"])
					name.content = value
					place.identified_by = name
					
					death.took_place_at = place
					
					entity.died = death
	
	# Map Activity Begin Date (If Known)
	def mapActivityBeginDate(self, entity, data):
		# a = Activity()
		# a.id = self.generateEntityURI(sub=["active", "from"])
		# p.carried_out = a
		pass
	
	# Map Activity End Date (If Known)
	def mapActivityEndDate(self, entity, data):
		# a = Activity()
		# a.id = self.generateEntityURI(sub=["active", "to"])
		# p.carried_out = a
		pass
	
	# Map Nationality
	def mapNationality(self, entity, data):
		nationality = get(data, "display.nationality")
		if(nationality):
			classification = get(nationality, "classification")
			if(classification):
				type = Type()
				type.id = get(classification, "id")
				type._label = get(classification, "label")
				type.classified_as = Type(ident="http://vocab.getty.edu/aat/300379842", label="Nationality")
				
				entity.classified_as = type
	
	# Map Biography
	def mapBiography(self, entity, data):
		biography = get(data, "display.biography.display.value")
		if(biography):
			lobj = LinguisticObject()
			lobj.id = self.generateEntityURI(sub=["biography"])
			lobj.content = biography
			lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300080102/", label="Biography Statement")
			
			entity.referred_to_by = lobj