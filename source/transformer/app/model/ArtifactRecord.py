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

import os
import json

class ArtifactRecord(BaseRecord):
	
	def __init__(self, id):
		super().__init__(id)
		self.resource = "artifact"
		self.cultures = self.loadCultures()
		# self.info()
	
	def entityType(self):
		return Object
	
	def loadCultures(self):
		with open(os.path.dirname(os.path.abspath(__file__)) + "/../data/Cultures.json", "r") as file:
			content = file.read()
		
		if(content):
			cultures = json.loads(content)
			
			if(cultures):
				return cultures
		
		return None
	
	def loadMaterials(self):
		with open(os.path.dirname(os.path.abspath(__file__)) + "/../data/Materials.json", "r") as file:
			content = file.read()
		
		if(content):
			materials = json.loads(content)
			
			if(materials):
				return materials
		
		return None
	
	# Map Entity Label
	def mapEntityLabel(self, entity, data):
		entity._label = get(data, "display.title.display.value", default="Object(" + str(self.id) + ")")
	
	# Map RightsStatements.org Assertion
	def mapRightsStatement(self, entity, data):
		assertion = get(data, "display.images.rights.display.value")
		if(assertion):
			link = get(data, "display.images.rights.display.uri")
			if(link):
				lobj = LinguisticObject()
				lobj.id = link
				lobj._label = "RightsStatements.org Rights Assertion"
				lobj.content = assertion
				
				# Map the "Rights Statement" classification
				lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300055547", label="Rights Statement")
				
				# Map the "Brief Text" classification
				lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300418049", label="Brief Text")
				
				entity.referred_to_by = lobj
	
	# Map Classifications
	def mapClassifications(self, entity, data):
		# Map the standard "Artwork" classification for all Objects (Artifacts) in this data set
		entity.classified_as = Type(ident="http://vocab.getty.edu/aat/300133025", label="Artwork")
		
		# Set defined Object Classification if available
		classification = get(data, "display.classification")
		if(classification):
			# debug(classification, format="JSON")
			
			entity.classified_as = Type(ident=get(classification, "classification.id"), label=get(classification, "classification.label"))
	
	# Map Accession Number
	def mapAccessionNumber(self, entity, data):
		number = get(data, "display.number.display.value")
		if(number):
			number_id = get(data, "display.number.uuid")
			if(number_id):
				identifier = Identifier()
				identifier.id = self.generateEntityURI(sub=["identifier", number_id])
				identifier._label = "Accession Number"
				identifier.content = number
				
				# Map the "Accession Number" classification
				identifier.classified_as = Type(ident="http://vocab.getty.edu/aat/300312355", label="Accession Number")
				
				entity.identified_by = identifier
	
	# Map Primary Title
	def mapPrimaryTitle(self, entity, data):
		title = get(data, "display.title.display.value")
		if(title):
			title_id = get(data, "display.title.uuid")
			if(title_id):
				name = Name()
				name.id = self.generateEntityURI(sub=["name", title_id])
				name._label = "Primary Title"
				name.content = title
				
				# Map the "Primary Title" classification
				# This is important as it denotes this title is the primary title associated with the work
				name.classified_as = Type(ident="http://vocab.getty.edu/aat/300404670", label="Primary Title")
				
				entity.identified_by = name
	
	# Map Alternate Titles
	def mapAlternateTitles(self, entity, data):
		titles = get(data, "display.titles")
		if(titles and len(titles) > 0):
			for key in titles:
				title = titles[key]
				if(title):
					value = get(title, "display.value")
					if(value):
						id = get(title, "uuid")
						if(id):
							# Exclude the following title subtypes...
							if(get(title, "subtype") not in [
								"PRIMARY TITLE",
								"GETTYGUIDE SEARCH TITLE",
								"GETTYGUIDE MIDDLE TITLE",
								"GETTYGUIDE SHORT TITLE",
							]):
								name = Name()
								name.id = self.generateEntityURI(sub=["name", id])
								name._label = get(title, "display.label", default="Alternate Title")
								name.content = value
								
								entity.identified_by = name
	
	# Map Object Description
	def mapDescription(self, entity, data):
		description = get(data, "display.description.display.value")
		if(description):
			id = get(data, "display.description.uuid")
			if(id):
				lobj = LinguisticObject()
				lobj.id = self.generateEntityURI(sub=["description", id])
				lobj.content = description
				
				# Map the "Description" classification
				lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300080091", label="Description")
				
				# Map the "Brief Text" classification
				lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300418049", label="Brief Text")
				
				entity.referred_to_by = lobj
	
	# Map Object Culture Statement/Type
	def mapCulture(self, entity, data):
		culture = get(data, "display.culture.display.value")
		if(culture):
			id = get(data, "display.culture.uuid")
			if(id):
				# Add a LinguisticObject via the "referred_to_by" property on the object
				# Add a classified_as to the LinguisticObject of type http://vocab.getty.edu/aat/300055768 (culture)
				
				lobj = LinguisticObject()
				lobj.id = self.generateEntityURI(sub=["culture", id])
				lobj.content = culture
				
				# Map the "Culture" classification
				lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300055768", label="Culture")
				
				# Map the "Brief Text" classification
				lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300418049", label="Brief Text")
				
				entity.referred_to_by = lobj
			
			# Add a Type to the Object via its "classified_as" property that points to the AAT ID for the matched culture
			# where we can find an exact match; also add a "classified_as" to the Type of http://vocab.getty.edu/aat/300055768 (culture);
			# This allows us to convey both the literal string as well as (where known) the exact match for the AAT vocabulary term
			if(culture in self.cultures):
				info = self.cultures[culture]
				if(info):
					type = Type()
					type.id = info["id"];
					type._label = info["label"];
					
					# Map the "Culture" classification
					type.classified_as = Type(ident="http://vocab.getty.edu/aat/300055768", label="Culture")
					
					entity.classified_as = type;
	
	# Map Object Material Statement (Medium)
	def mapMaterialStatement(self, entity, data):
		medium = get(data, "display.medium.display.value")
		if(medium):
			id = get(data, "display.medium.uuid")
			if(id):
				lobj = LinguisticObject()
				lobj.id = self.generateEntityURI(sub=["material-statement", id])
				lobj.content = medium
				
				# Map the "Material Statement" classification
				lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300010358", label="Material Statement")
				
				# Map the "Brief Text" classification
				lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300418049", label="Brief Text")
				
				entity.referred_to_by = lobj
	
	# Map Object Materials (Medium)
	def mapMaterials(self, entity, data):
		medium = get(data, "display.medium.display.value")
		if(medium):
			# Load our Materials mapping for the AAT Vocabulary
			materials = self.loadMaterials()
			if(materials):
				# If the current medium string matches one of the defined and populated mappings
				if((medium in materials) and len(materials[medium]) > 0):
					# Iterate through the mapped materials
					for material in materials[medium]:
						# debug(material, format="JSON")
						
						# Then map them via Material entities to the Object via the "made_of" property
						if(has(material, "id") and has(material, "label")):
							entity.made_of = Material(ident=get(material, "id"), label=get(material, "label"))
	
	# Map Object Inscriptions
	def mapInscriptions(self, entity, data):
		inscriptions = get(data, "display.marks.inscriptions")
		if(inscriptions):
			# Add a LinguisticObject via the "carries" property on the Object
			# Add a classified_as to the LinguisticObject of Type http://vocab.getty.edu/aat/300028702 (inscriptions)
			for inscription in inscriptions:
				value = get(inscription, "display.value")
				if(value):
					id = get(inscription, "uuid")
					if(id):
						lobj = LinguisticObject()
						lobj.id = self.generateEntityURI(sub=["inscription", id])
						lobj.content = value
						
						# Map the "Inscription" classification
						lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300028702", label="Inscriptions")
						
						# Map the "Brief Text" classification
						lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300418049", label="Brief Text")
						
						entity.carries = lobj;
	
	# Map Object Markings
	def mapMarkings(self, entity, data):
		markings = get(data, "display.marks.markings")
		if(markings):
			# Add a LinguisticObject via the "carries" property on the Object
			# Add a classified_as to the LinguisticObject of Type http://vocab.getty.edu/aat/300028744 (marks (symbols))
			for marking in markings:
				value = get(marking, "display.value")
				if(value):
					id = get(marking, "uuid")
					if(id):
						lobj = LinguisticObject()
						lobj.id = self.generateEntityURI(sub=["mark", id])
						lobj.content = value
						
						# Map the "Marks (Symbols)" classification
						lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300028744", label="Marks (Symbols)")
						
						# Map the "Brief Text" classification
						lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300418049", label="Brief Text")
						
						entity.carries = lobj;
	
	# Map Object Signatures
	def mapSignature(self, entity, data):
		signatures = get(data, "display.marks.signature")
		if(signatures):
			# Add a LinguisticObject via the "carries" property on the Object
			# Add a classified_as to the LinguisticObject of Type http://vocab.getty.edu/aat/300028705 (signatures (names))
			for signature in signatures:
				value = get(signature, "display.value")
				if(value):
					id = get(signature, "uuid")
					if(id):
						lobj = LinguisticObject()
						lobj.id = self.generateEntityURI(sub=["signature", id])
						lobj.content = value
						
						# Map the "Signatures (Names)" classification
						lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300028705", label="Signatures (Names)")
						
						# Map the "Brief Text" classification
						lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300418049", label="Brief Text")
						
						entity.carries = lobj;
	
	# Map Object Watermarks
	def mapWatermarks(self, entity, data):
		watermarks = get(data, "display.marks.watermarks")
		if(watermarks):
			# Add a LinguisticObject via the "carries" property on the Object
			# Add a classified_as to the LinguisticObject of Type http://vocab.getty.edu/aat/300028749 (watermarks)
			for watermark in watermarks:
				value = get(watermark, "display.value")
				if(value):
					id = get(watermark, "uuid")
					if(id):
						lobj = LinguisticObject()
						lobj.id = self.generateEntityURI(sub=["watermark", id])
						lobj.content = value
						
						# Map the "Watermarks" classification
						lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300028749", label="Watermarks")
						
						# Map the "Brief Text" classification
						lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300418049", label="Brief Text")
						
						entity.carries = lobj;
	
	# Map Object Place Created
	def mapPlaceCreated(self, entity, data):
		pass
	
	# Map Object Place Depicted
	def mapPlaceDepicted(self, entity, data):
		depicted = get(data, "display.places.depicted.display.value")
		if(depicted):
			id = get(data, "display.places.depicted.uuid")
			if(id):
				visual = VisualItem()
				visual.id = self.generateEntityURI(sub=["shows", id])
				
				place = Place()
				place.id = self.generateEntityURI(sub=["place", id])
				place._label = depicted
				
				name = Name()
				name.id = self.generateEntityURI(sub=["place", "name", id])
				name.content = depicted
				
				place.identified_by = name
				
				# Map the "Inhabited Place" classification
				place.classified_as = Type(ident="http://vocab.getty.edu/aat/300008347", label="Inhabited Place")
				
				visual.represents = place
				
				entity.shows = visual
	
	# Map Object Place Found
	def mapPlaceDepicted(self, entity, data):
		pass
	
	# Map Object Main Image
	def mapMainImage(self, entity, data):
		image = get(data, "display.images.display")
		if(image):
			derivative = None
			
			if(has(image, "derivatives.larger")):
				derivative = get(image, "derivatives.larger")
			elif(has(image, "derivatives.enlarge")):
				derivative = get(image, "derivatives.enlarge")
			elif(has(image, "derivatives.thumbnail")):
				derivative = get(image, "derivatives.thumbnail")
			
			# debug(derivative, format="JSON")
			
			if(derivative):
				derivativeURL = get(derivative, "url")
				if(derivativeURL):
					visual = VisualItem();
					
					# Specify the image URL
					visual.id = derivativeURL
					
					# Specify the image view label
					visual._label = get(image, "view", default="Main View")
					
					# Specify the image MIME type format
					visual.format = get(image, "mime")
					
					# Map the "Digital Image" classification
					visual.classified_as = Type(ident="http://vocab.getty.edu/aat/300215302", label="Digital Image")
					
					# TODO How do we add InformationObjects to images? How do we define administrative attributes this way?
					# info = InformationObject()
					# info.id = "http://media.getty.edu/museum/images/web/larger/00094701.jpg/information/"
					# info.content = "hello";
					# visual.information = info
					
					entity.representation = visual
	
	# Map Alternate Images
	def mapAlternateImages(self, entity, data):
		pass
	
	# Map Object Home Page
	def mapHomePage(self, entity, data):
		id = get(data, "id")
		if(id):
			# Web pages are referenced via LinguisticObject entities
			lobj = LinguisticObject()
			
			# Here we generate the full URL for the object homage page
			lobj.id = "http://www.getty.edu/art/collection/objects/" + str(id) + "/"
			lobj._label = "Homepage for Object"
			
			# Map the MIME type format for the referenced content
			lobj.format = "text/html"
			
			# Map the "Web Page" classification
			lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300264578", label="Web Page")
			
			# Map the "Primary" classification to note that this LinguisticObject references the canonical web page for the Object
			lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300404670", label="Primary")
			
			entity.subject_of = lobj
	
	# Map Object Curatorial Department
	def mapCuratorialDepartment(self, entity, data):
		# For now add the Curatorial Department as a Group
		# that is a "member_of" the Group (organization) the J. Paul Getty Trust Musuem/Trust
		# and relate this to the Object entity via the "current_keeper" relationship.
		# This will need to be refactored later with a more accurate pattern that allows
		# for the Curatorial Department's oversight to be maintained even if the Object is on loan
		# and thus should temporarily have a different "current_keeper" assigned
		
		value = get(data, "display.department.display.value")
		if(value):
			id = get(data, "display.department.uuid")
			if(id):
				# Create a Group to represent the Curatorial Department
				group = Group()
				group.id = self.generateEntityURI(entity=Group, UUID=id)
				group._label = value + " (Curatorial Department)"
				
				# Obtain a copy of the J. Paul Getty Museum Group
				group.member_of = self.createGettyMuseumGroup(); # defined in BaseRecord.py
				
				# Map the "Department (Organizational Unit)" classification
				group.classified_as = Type(ident="http://vocab.getty.edu/aat/300263534", label="Department (Organizational Unit)");
				
				# Map the Curatorial Department's name for the Group
				name = Name()
				name.id = self.generateEntityURI(sub=["department", id, "name"])
				name.content = value
				
				group.identified_by = name
				
				# Map the Group to the Object's "current_keeper" property for now...
				entity.current_keeper = group
	
	# Map Object Current Owner
	def mapCurrentOwner(self, entity, data):
		# Get the Museum's Collection status for the Object
		status = get(data, "status")
		if(status):
			# If the status is "PERMANENT COLLECTION"
			if(status == "PERMANENT COLLECTION"):
				# Note that the Object is currently owned by the J. Paul Getty Museum
				owner = self.createGettyMuseumGroup();
				if(owner):
					# Create the Acquisition activity
					aquisition = Acquisition()
					aquisition.id = self.generateEntityURI(sub=["activity", "acquisition"])
					aquisition._label = "Acquisition"
					
					# Associate the Acquisition activity with the owner via the "acquired_title_through" property
					owner.acquired_title_through = aquisition
					
					# Then assign the "current_owner" relationship for the Object
					entity.current_owner = owner
	
	# Map Object Current Location
	def mapCurrentLocation(self, entity, data):
		location = get(data, "display.location")
		if(location):
			id = get(data, "display.location.uuid")
			
			# Add Object's Current Location (Gallery/Storage)
			place = Place()
			place.id = self.generateEntityURI(entity=Place, UUID=id)
			
			# Obtain the Object's current location display value (name)
			value = get(location, "display.value") # e.g. "Getty Center, Museum West Pavilion, Gallery W204"
			if(value):
				place._label = value
				
				name = Name()
				name.id = self.generateEntityURI(entity=Place, UUID=id, sub=["name"])
				name.content = value
				
				place.identified_by = name
			
			entity.current_location = place
	
	# Map Object Dimensions
	def mapDimensions(self, entity, data):
		dimensions = get(data, "display.dimensions")
		if(dimensions):
			id = get(dimensions, "uuid")
			if(id):
				# Add Object Dimensions Statement
				statement = get(dimensions, "display.value")
				if(statement):
					lobj = LinguisticObject()
					lobj.id = self.generateEntityURI(sub=["dimensions", id])
					lobj.content = statement
					
					# Map the "Dimension Statement" classification
					lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300266036", label="Dimension Statement")
					
					# Map the "Brief Text" classification
					lobj.classified_as = Type(ident="http://vocab.getty.edu/aat/300418049", label="Brief Text")
					
					entity.referred_to_by = lobj
				
				# Map any available dimensions measurements
				measurements = get(dimensions, "measurements")
				if(measurements and len(measurements) > 0):
					for measurement in measurements:
						value = get(measurement, "display.value")
						if(value):
							id = get(measurement, "uuid")
							if(id):
								# Map the dimension value
								dimension = Dimension()
								dimension.id = self.generateEntityURI(sub=["dimension", id])
								dimension.value = value
								
								# Map the dimension measurement classification, e.g. Width
								classification = get(measurement, "classification")
								if(classification):
									dimension.classified_as = Type(ident=get(classification, "id"), label=get(classification, "label"))
								
								# Map the dimension measurement unit classification, e.g. Centimeters
								classification = get(measurement, "unit.classification")
								if(classification):
									dimension.unit = MeasurementUnit(ident=get(classification, "id"), label=get(classification, "label"))
								
								entity.dimension = dimension
	
	# Map Object Artist/Maker Relationship(s)
	def mapArtistMakerRelationships(self, entity, data):
		makers = get(data, "display.makers")
		if(makers and len(makers) > 0):
			# Obtain the Object's Date
			date = get(data, "display.date")
			# debug(date, format="JSON")
			
			# Obtain the Object's Place Created (if available)
			created = get(data, "display.places.created")
			# debug(created, format="JSON")
			
			for maker in makers:
				# debug(maker, format="JSON")
				
				id    = get(maker, "uuid") # Maker UUID
				value = get(maker, "display.value") # Maker name
				if(id and value):
					person = Person()
					person.id = self.generateEntityURI(entity=Person, UUID=id)
					person._label = value
					
					if(date):
						# Add a Name to the TimeSpan of the Prodction activity to store the display date string
						name = Name();
						name.id = self.generateEntityURI(sub=["activity", "production", id, "timespan", "name"])
						name._label = "Date"
						name.content = get(date, "display.value")
						
						# Map the "Dates (Spans of Time)" classification
						name.classified_as = Type(ident="http://vocab.getty.edu/aat/300404439", label="Dates (Spans of Time)")
						
						timespan = TimeSpan()
						timespan.id = self.generateEntityURI(sub=["activity", "production", id, "timespan"])
						timespan.identified_by = name
						
						# NOTE Should we also classify the timespan? presumably it is implicit, but is it helpful to do so?
						timespan.classified_as = Type(ident="http://vocab.getty.edu/aat/300404439", label="Dates (Spans of Time)")
						
						# Get the padded lower and upper date values
						lower = get(date, "value.lower")
						upper = get(date, "value.upper")
						
						# Clarify if we should treat "begin_of_the_begin" and "end_of_the_begin"
						# or "begin_of_the_end" and "end_of_the_end" differently than we do below
						
						if(lower):
							timespan.begin_of_the_begin = lower
							timespan.end_of_the_begin   = lower
						
						if(upper):
							timespan.begin_of_the_end   = upper
							timespan.end_of_the_end     = upper
					
					# Create the Production activity instance
					production = Production()
					production.id = self.generateEntityURI(sub=["activity", "production", id])
					production._label = "Production of Artwork"
					
					# Associate the Production activity TimeSpan (this is overall timespan (dates) for the creation of the Object)
					production.timespan = timespan
					
					# TODO How do we add the timespan that this given artist (Person) was involved with the production of the Object?
					# See https://linked.art/model/provenance/production.html#multiple-artists-with-roles
					production.carried_out_by = person
					
					# TODO How do we assign a Place Created to each Maker's involvement, as mutliple creation places may be
					# involved, one (or maybe more) for each maker, for different timespans of creation of the work?
					
					# Object Place Created
					# Add via the "took_place_at" property of the Production activity
					if(created):
						place = Place()
						place.id = self.generateEntityURI(entity=Place, UUID=get(created, "uuid"))
						place._label = get(created, "display.value")
						
						# Map the place name
						name = Name()
						name.id = self.generateEntityURI(entity=Place, UUID=get(created, "uuid"), sub=["name"])
						name.content = get(created, "display.value")
						
						# Map the place name
						place.identified_by = name
						
						# Map the "Inhabited Place" classification
						place.classified_as = Type(ident="http://vocab.getty.edu/aat/300008347", label="Inhabited Place")
						
						production.took_place_at = place
					
					entity.produced_by = production
