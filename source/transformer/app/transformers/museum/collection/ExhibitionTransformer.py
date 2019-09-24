# Import our application utility functions
from app.utilities import get, has, debug, sprintf

# Import our dependency injector
from app.di import DI

# Import our Museum Collection BaseTransformer class
from app.transformers.museum.collection.BaseTransformer import BaseTransformer

from app.di import DI

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

class ExhibitionTransformer(BaseTransformer):
	
	def activityStreamObjectTypes(self):
		"""Provide a method for conveying the supported Activity Stream Object type names that this transformer will handle"""
		return [
			"Exhibition",
		]
	
	def resourceType(self):
		return "exhibition"
	
	def entityType(self):
		return Exhibition
	
	def entityName(self):
		"""Provide a method for determining the correct target entity type name"""
		return "Exhibition"
	
	# Map Exhibition Classification
	def mapClassification(self, entity, data):
		entity.classified_as = Type(ident="http://vocab.getty.edu/aat/300417531", label="Exhibition")
	
	# Map Exhibition Title
	def mapTitle(self, entity, data):
		title = get(data, "display.title.display.value")
		if(title):
			name = Name(ident=self.generateEntityURI(sub=["name"]), label="Display Title")
			
			name.content = title
			
			name.classified_as = Type(ident="http://vocab.getty.edu/aat/300417193", label="Titles (General, Names)")
			
			name.classified_as = Type(ident="http://vocab.getty.edu/aat/300404670", label="Preferred Term")
			
			entity.identified_by = name
	
	# Map Exhibition Curators
	def mapCurators(self, entity, data):
		curators = get(data, "display.related.curators")
		if(isinstance(curators, list) and len(curators) > 0):
			creation = Creation(ident=self.generateEntityURI(sub=["creation"]))
			
			for curator in curators:
				person = Person(ident=self.generateEntityURI(entity=Person, id=get(curator, "uuid")), label=get(curator, "display.value"))
				person.classified_as = Type(ident="http://vocab.getty.edu/aat/300025633", label="Curators")
				person.classified_as = Type(ident="http://vocab.getty.edu/aat/300417893", label="Exhibition Curators")
				
				creation.carried_out_by = person
			
			entity.created_by = creation
	
	# Map Exhibition Activities
	def mapActivities(self, entity, data):
		venues = get(data, "display.related.venues")
		if(isinstance(venues, list) and len(venues) > 0):
			manager = DI.get("manager")
			if(not manager):
				raise RuntimeError(sprintf("%s.mapActivities() Failed to obtain Manager instance!" % (self.__class__.__name__)))
			
			# Wrapper Activity for travelling exhibitions
			travelling = None
			
			events = get(data, "display.related.events")
			if(isinstance(events, list) and len(events) > 0):
				for event in events:
					# debug(event, format="JSON")
					
					# Determine if the exhibition is a travelling exhibition or not, by looking for the travelling exhibition event
					if(event["type"] == "EXHIBITION" and event["subtype"] == "TRAVELLING" and event["primary"] == True):
						travelling = Activity(ident=self.generateEntityURI(entity=Activity, UUID=get(event, "uuid")))
						
						travelling._namespace = self.getNamespace()
						travelling._uuid      = get(event, "uuid")
						travelling._label     = sprintf("Travelling Exhibition for %s" % (get(data, "display.title.display.value", default=get(event, "uuid"))))
						
						travelling.classified_as = Type(ident="http://vocab.getty.edu/aat/300054766", label="Exhibitions (Events)")
						
						travelling.classified_as = Type(ident="http://vocab.getty.edu/aat/300054773", label="Travelling Exhibitions")
			
			if(travelling):
				dates = get(data, "display.dates")
				if(dates):
					timespan = TimeSpan(ident=self.generateEntityURI(entity=Activity, UUID=get(event, "uuid"), sub=["timespan"]))
					
					began = get(dates, "range.began.values.iso")
					if(began):
						timespan.begin_of_the_begin = began
					
					ended = get(dates, "range.ended.values.iso")
					if(ended):
						timespan.end_of_the_end = ended
					
					travelling.timespan = timespan
			
			for venue in venues:
				# debug(venue, format="JSON")
				
				# Create a venue exhibition activity instance for each venue
				activity = Activity(ident=self.generateEntityURI(entity=Activity, UUID=get(venue, "activity.uuid")))
				
				activity._namespace = self.getNamespace()
				activity._uuid      = get(venue, "activity.uuid")
				activity._label     = sprintf("Exhibting %s at %s" % (get(data, "display.title.display.value"), get(venue, "display.value")))
				
				activity.classified_as = Type(ident="http://vocab.getty.edu/aat/300054766", label="Exhibitions (Events)")
				
				dates = get(venue, "activity.dates")
				if(dates):
					timespan = TimeSpan(ident=self.generateEntityURI(entity=Activity, UUID=get(venue, "activity.uuid"), sub=["timespan"]))
					
					began = get(dates, "range.began.values.iso")
					if(began):
						timespan.begin_of_the_begin = began
					
					ended = get(dates, "range.ended.values.iso")
					if(ended):
						timespan.end_of_the_end = ended
					
					activity.timespan = timespan
				
				place = Place(ident=self.generateEntityURI(entity=Place, UUID=get(venue, "uuid")), label=get(venue, "display.value"))
				
				classifications = get(venue, "classifications")
				if(isinstance(classifications, list) and len(classifications) > 0):
					for classification in classifications:
						place.classified_as = Type(ident=get(classified, "id"), label=get(classified, "label"))
				
				activity.took_place_at = place
				
				organizers = get(venue, "organizers")
				if(isinstance(organizers, list) and len(organizers) > 0):
					for organizer in organizers:
						# debug(organizer, format="JSON")
						
						if(get(organizer, "type") == "INDIVIDUAL"):
							actor = Person(ident=self.generateEntityURI(entity=Person, UUID=get(organizer, "uuid")))
						else:
							actor = Group(ident=self.generateEntityURI(entity=Group, UUID=get(organizer, "uuid")))
						
						actor._label = get(organizer, "display.value")
						
						actor.classified_as = Type(ident="http://vocab.getty.edu/aat/300025633", label="Organizer")
						
						activity.carried_out_by = actor
				
				objects = get(venue, "objects")
				if(isinstance(objects, list) and len(objects) > 0):
					set = Set(ident=self.generateEntityURI(entity=Activity, UUID=get(venue, "activity.uuid"), sub=["objects"]))
					
					for object in objects:
						# debug(object, format="JSON")
						
						artifact = Object(ident=self.generateEntityURI(entity=Object, UUID=get(object, "uuid"), entityName="object"), label=get(object, "display.value"))
						
						classifications = get(object, "classifications")
						if(isinstance(classifications, list) and len(classifications) > 0):
							for classification in classifications:
								artifact.classified_as = Type(ident=get(classified, "id"), label=get(classified, "label"))
						
						set.member = artifact
					
					activity.used_specific_object = set
				
				if(manager.storeEntity(activity)):
					if(travelling):
						part = Activity(ident=self.generateEntityURI(entity=Activity, UUID=get(venue, "uuid")), label=None)
						
						part.classified_as = Type(ident="http://vocab.getty.edu/aat/300054766", label="Exhibitions (Events)")
						
						if(activity._label):
							part._label = activity._label
						
						if(activity.timespan):
							part.timespan = activity.timespan
						
						travelling.part = part
					else:
						entity.motivated = Activity(ident=activity.id, label=activity._label)
				else:
					debug("%s.mapActivities() Failed to store Activity (%s) entity for Exhibition (%s) entity!" % (self.__class__.__name__, activity, entity), error=True)
			
			if(travelling):
				if(manager.storeEntity(travelling)):
					entity.motivated = Activity(ident=travelling.id, label=travelling._label)
				else:
					debug("%s.mapActivities() Failed to store Activity (%s) entity for Exhibition (%s) entity!" % (self.__class__.__name__, activity, entity), error=True)
	
	# Map Exhibition Aboutness
	def mapAboutness(self, entity, data):
		pass
