import copy
import inspect
import json
import os
import requests
import sys

# Import abstract class/method extensions from the extended abcplus (abc) module
from abcplus import ABC, abstractmethod, finalmethod

# Import our utility functions
from app.utilities import *

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

transformers = {}

def registerTransformers():
	debug("app.transformers.registerTransformers() called...", level=1)
	
	global transformers
	
	# Obtain the absolute (real) path to this current script file;
	# as all of our transformers are located beneath this script, we
	# can use the path to this script as the starting point for our
	# directory traversal as we look for and register each transformer
	file = os.path.realpath(__file__)
	if(file):
		# Obtain the directory path name for this script file
		baseDir = os.path.dirname(file)
		if(baseDir):
			# traverse the directory hierarchy to find transformers
			for dirName, subDirList, fileList in os.walk(baseDir):
				if(len(dirName) > len(baseDir)):
					# Obtain the file/directory's base name
					baseName = os.path.basename(dirName)
					# Ignore any special double-underscore Python files and directories
					if(not (baseName.startswith("__") and baseName.endswith("__"))):
						# debug(dirName)
						# debug(subDirList)
						# debug(fileList)
						
						for file in fileList:
							# Ignore any hidden or temp files
							if(not (file.startswith(".") or file.startswith("_"))):
								# Filter out any non-Transformer classes
								if(file.endswith("Transformer.py")):
									# Ignore any Base Transformer classes; these
									# do not need registering directly; they will
									# be imported by their subclasses as needed
									if(not file.startswith("Base")):
										# Use the directory name of the transformer, less the base
										# directory as the namespace for this transformer
										namespace = os.path.relpath(dirName, baseDir)
										
										# debug("%s, %s, %s" % (baseDir, dirName, namespace))
										# debug(" - %s, %s" % (namespace, (dirName, file)))
										
										modName = os.path.splitext(file)[0];
										modPath = os.path.join(dirName, modName).strip("/").split("/")
										
										# debug("Will try to import: %s from %s" % (modName, modPath))
										# debug()
										
										transformer = {
											"file": {
												"path": dirName,
												"name": file,
											},
											"module": {
												"path":  modPath,
												"name":  modName,
												"class": None,
											},
											"stream": {
												"endpoint": None,
												"options": None,
												"namespace": namespace,
												"types": None,
											},
										}
										
										# Import the found transformer module
										module = __import__(".".join(modPath), fromlist=modName)
										if(module):
											# debug("Successfully imported module: %s from %s" % (modName, modPath))
											
											# Obtain the class constructor from the module
											klass = getattr(module, modName)
											if(klass):
												transformer["module"]["class"] = klass

												# Register the class globally
												globals()[modName] = klass
												
												# Create an instance of the transformer class
												instance = klass()
												if(instance):
													endpointURL = instance.activityStreamEndpoint()
													if(isinstance(endpointURL, str) and len(endpointURL) > 0):
														transformer["stream"]["endpoint"] = endpointURL
													
													endpointOptions = instance.activityStreamEndpointOptions()
													if(isinstance(endpointOptions, dict) and len(endpointOptions) > 0):
														transformer["stream"]["options"] = endpointOptions
													
													# Obtain our transformer class' metadata for registration
													types = instance.activityStreamObjectTypes()
													if(isinstance(types, list) and len(types) > 0):
														transformer["stream"]["types"] = types
													else:
														raise RuntimeError(sprintf("Failed to obtain a list of the %s transformer's supported Activity Stream types!" % (modName)))
										else:
											raise RuntimeError(sprintf("Failed to import %s from %s!" % (modName, modPath)))
										
										if(namespace in transformers):
											transformers[namespace].append(transformer)
										else:
											transformers[namespace] = [transformer]

def registeredTransformers():
	global transformers
	
	return transformers

def transformerForEntity(entity=None, namespace=None):
	global transformers
	
	if(isinstance(entity, str) and len(entity) > 0):
		if(transformers):
			for transformerNamespace in transformers:
				if(namespace == None or namespace == transformerNamespace):
					for transformer in transformers[transformerNamespace]:
						types = get(transformer, "stream.types")
						if(isinstance(types, list) and len(types) > 0):
							if(entity in types):
								klass = get(transformer, "module.class")
								if(klass):
									return klass

# Abstract shared BaseTransformer class for all Transformer subclasses
class BaseTransformer(ABC):
	
	def __init__(self, *args, id=None, URL=None, **kwargs):
		"""Initialise the BaseTransformer class"""
		
		# if the named 'id' argument has not been provided
		# but a single positional argument has, treat it as
		# the record identifier instead
		if(id == None):
			if(args and len(args) == 1):
				if(args[0]):
					id = args[0]
		
		debug("%s.__init__(id: %s, URL: %s) called..." % (self.__class__.__name__, id, URL), level=1)
		
		self.className = self.__class__.__name__
		self.id        = id
		self.recordURL = URL # NOTE DEPRECATED NEED TO REMOVE
		self.UUID      = None
		self.entity    = None
		self.data      = None
	
	def __str__(self):
		debug("%s.__str__() called..." % (self.__class__.__name__), level=1)
		
		name = self.getEntityName()
		if(name):
			space = self.getNamespace()
			if(space):
				name = space.replace("/", ".") + "." + name
			
			uuid = self.getUUID()
			if(uuid):
				return sprintf("<%s(%s)>" % (name, uuid))
			else:
				return sprintf("<%s>" % (name))
		
		return super().__str__()
	
	@abstractmethod
	def activityStreamEndpoint(self):
		"""Provide a method for conveying the Activity Stream endpoint that this transformer will process"""
		pass
	
	@abstractmethod
	def activityStreamEndpointOptions(self):
		"""Provide a method for conveying the Activity Stream endpoint options to configure each HTTP request"""
		pass
	
	@abstractmethod
	def activityStreamObjectTypes(self):
		"""Provide a method for conveying the supported Activity Stream Object type names that this transformer will handle"""
		pass
	
	@abstractmethod
	def entityType(self):
		"""Provide a method for determining the correct target entity type"""
		pass
	
	@finalmethod
	def entityTypeName(self, **kwargs):
		"""Provide a method for determining the correct target entity type name"""
		
		if("entity" in kwargs):
			entity = kwargs["entity"]
		else:
			entity = self.entityType()
		
		if(entity):
			if(isinstance(entity, type)):
				if(entity == self.entityType()):
					if(hasattr(self, "entityName") and callable(self.entityName)):
						return self.entityName()
				
				entity = entity()
			else:
				if(isinstance(entity, self.entityType())):
					if(hasattr(self, "entityName") and callable(self.entityName)):
						return self.entityName()
			
			if(entity):
				return entity.__class__.__name__
		
		return None
	
	@abstractmethod
	def assembleHeaders(self):
		"""Assemble our HTTP Request Headers for the DOR API call"""
		pass
	
	@abstractmethod
	def generateURI(self):
		"""Generate the URI for a DOR API resource"""
		pass
	
	@abstractmethod
	def generateURL(self):
		"""Generate the absolute URL for a DOR API resource"""
		pass
	
	def generateEntityName(self, **kwargs):
		"""Generate an hyphenated entity name for the current or provided entity for use in URIs/URLs"""
		
		debug("%s.generateEntityName(%s) called..." % (self.__class__.__name__, kwargs), level=1)
		
		entity = copy.copy(self.entity)
		
		if("entity" in kwargs):
			if(kwargs["entity"]):
				entity = kwargs["entity"]
		
		if(entity):
			# If the passed entity is a type, not an object
			if(isinstance(entity, type)):
				# Instantiate it so that we can correctly determine its class name
				entity = entity()
			
			if(entity):
				className = self.entityTypeName(entity=entity)
				if(isinstance(className, str) and len(className) > 0):
					return hyphenatedStringFromCamelCasedString(className)
		
		return None
	
	def generateEntityURI(self, **kwargs):
		"""Generate an entity URI for the current or provided entity"""
		
		debug("%s.generateEntityURI(%s)" % (self.__class__.__name__, kwargs), level=1)
		
		if("namespace" in kwargs):
			namespace = kwargs["namespace"]
			del kwargs["namespace"]
		else:
			namespace = self.getNamespace()
		
		if(not (isinstance(namespace, str) and len(namespace) > 0)):
			raise RuntimeError("Invalid namespace parameter! It must be a valid, non-empty string!")
		
		entity = None
		
		if("entity" in kwargs):
			entity = kwargs["entity"]
			del kwargs["entity"]
		elif(self.entity):
			entity = self.entity
		
		if(not (entity and getattr(entity, "__module__", None) == "cromulent.model")):
			raise RuntimeError("Invalid entity parameter! It must be an instance of a CROM model type!")
		
		if("entityName" in kwargs):
			entityName = kwargs["entityName"]
			del kwargs["entityName"]
		else:
			entityName = self.generateEntityName(entity=entity);
		
		if(not (isinstance(entityName, str) and len(entityName) > 0)):
			raise RuntimeError("Unable to generate name for CROM entity!")
		
		if("UUID" in kwargs):
			UUID = kwargs["UUID"]
			del kwargs["UUID"]
		else:
			UUID = self.getUUID()
		
		if(not (isinstance(UUID, str) and len(UUID) > 0)):
			raise RuntimeError("Invalid UUID parameter! It must be a valid UUIDv4 string representation!")
		
		return self.assembleEntityURI(namespace=namespace, entityName=entityName, UUID=UUID, **kwargs)
	
	@classmethod
	def assembleEntityURI(cls, namespace=None, entityName=None, UUID=None, **kwargs):
		"""Assemble an entity URI for the current or provided entity"""
		
		debug("%s.assembleEntityURI(%s)" % (cls.__class__.__name__, kwargs), level=1)
		
		baseURL       = os.getenv("LOD_BASE_URL", None)
		trailingSlash = os.getenv("LOD_SLASH_URL", "YES")
		
		options = commandOptions({
			"slash": False,
		})
		
		if("slash" in options):
			if(isinstance(options["slash"], bool) and options["slash"] == True):
				trailingSlash = "YES"
		
		if(not (isinstance(baseURL, str) and len(baseURL) > 0)):
			raise RuntimeError("Missing or invalid 'LOD_BASE_URL' environment variable!")
		
		if(not (isinstance(namespace, str) and len(namespace) > 0)):
			raise RuntimeError("Missing or invalid namespace parameter!")
		
		if(not (isinstance(entityName, str) and len(entityName) > 0)):
			raise RuntimeError("Missing or invalid entity name parameter!")
		
		if(not (isinstance(UUID, str) and len(UUID) > 0)):
			raise RuntimeError("Missing or invalid UUID parameter!")
		
		URI = baseURL + "/" + namespace + "/" + entityName + "/" + UUID + "/"
		
		if("sub" in kwargs):
			if(isinstance(kwargs["sub"], list) and len(kwargs["sub"]) > 0):
				URI += "/".join(kwargs["sub"]) + "/"
		
		if(trailingSlash != "YES"):
			if(URI.endswith("/")):
				URI = URI[0:-1]
		
		return URI
	
	def getNamespace(self):
		"""Get the transformer's namespace based on the location of the transformer in the module hierarchy"""
		
		# debug("%s.generateNamespace() module name: %s" % (self.__class__.__name__, self.__module__), level=1)
		
		# obtain the current module name
		if(isinstance(self.__module__, str) and len(self.__module__) > 0):
			parts = self.__module__.split(".")
			if(isinstance(parts, list) and len(parts) > 2):
				# extract the middle of the module name, excluding the first two items and the last
				subparts = parts[2:-1]
				if(len(subparts) > 0):
					return "/".join(subparts)
		
		return None
	
	def getEntityName(self):
		return self.entityTypeName()
	
	@abstractmethod
	def getUUID(self):
		"""Provide a method for accessing the record's UUID"""
		
		debug("%s.getUUID() called..." % (self.__class__.__name__), level=1)
		
		pass
	
	def getData(self):
		"""Obtain the data for the specified DOR entity resource"""
		
		debug("%s.getData() called..." % (self.__class__.__name__), level=1)
		
		URL = self.generateURL()
		
		debug("Will now call URL: %s" % (URL), indent=1, level=2)
		
		if(isinstance(URL, str)):
			headers = self.assembleHeaders()
			if(isinstance(headers, dict)):
				response = requests.get(URL, headers=headers, timeout=90)
				if(response):
					if(response.status_code == 200):
						data = json.loads(response.text)
						if(isinstance(data, dict)):
							self.id   = get(data, "id")
							self.UUID = get(data, "uuid")
							self.data = data
							
							return data
						else:
							raise RuntimeError("Invalid JSON Data!")
					else:
						raise RuntimeError("Invalid HTTP Response Status Code!")
				else:
					raise RuntimeError("Invalid HTTP Response!")
			else:
				raise RuntimeError("Missing DOR API Version Environment Variable!")
		else:
			raise RuntimeError("The record URL was invalid!")
		
		return None
	
	def mapData(self):
		"""Orchestrate the data mapping process"""
		
		debug("%s.mapData() called..." % (self.__class__.__name__), level=1)
		
		# Create entity instance
		entityType = self.entityType()
		if(entityType):
			entity = entityType()
			if(entity):
				self.entity = entity
				
				# Assign entity ID
				self.entity.id = self.generateEntityURI()
			
				options = commandOptions({
					"source": False,
					"method": None,
				})
				
				if(options["source"]):
					if(options["source"] == True):
						debug(self.data, format="JSON", label="Debug Output for self.data:")
					elif(isinstance(options["source"], str) and len(options["source"]) > 0):
						debug(get(self.data, options["source"]), format="JSON", label=sprintf("self.data (%s):" % (options["source"])))
				
				methodNames = []
				# Now look for any class methods starting with the word "map";
				# we will then call any of the discovered "map" methods to update
				# the entity instance by mapping part of the data; we exclude
				# any calls to the "mapData" method below to prevent infinite recursion
				methods = inspect.getmembers(self, predicate=inspect.ismethod)
				for method in methods:
					if(method and method[0]):
						methodName = method[0];
						if(isinstance(methodName, str)):
							if(methodName.startswith("map")):
								if(methodName not in ["mapData"]):
									if(not methodName in methodNames):
										methodNames.append(methodName)
										
										# obtain a reference to the named method via getattr()
										mapMethod = getattr(self, methodName)
										if(mapMethod):
											# Run all methods if no test has been defined, or just the matching method
											if((options["method"] == None) or (options["method"] == methodName)):
												# As "self.entity" is passed by reference, it may be
												# updated directly by the called "map" method
												mapMethod(self.entity, self.data)
					
				# If the testMethod was invalid or not found, report the error
				if(isinstance(options["method"], str)):
					if(not options["method"].startswith("map")):
						debug("The specified method (%s.%s) does not begin with 'map'; only map methods are supported for this use-case!" % (self.__class__.__name__, options["method"]), error=True, indent=1)
					elif(options["method"] not in methodNames):
						debug("The specified method (%s.%s) does not exist!" % (self.__class__.__name__, options["method"]), error=True, indent=1)
				
				if(entity):
					return entity
				else:
					raise RuntimeError("Failed to Map CROM Entity () Instance!")
			else:
				raise RuntimeError("Failed to Instantiate CROM Entity () Instance!")
		else:
			raise RuntimeError("Failed to Obtain CROM Entity Type!")
		
		return None
	
	def toJSON(self, compact=False):
		"""Convert the mapped data into its JSON-LD serialization using CROM's Factory.toString() method"""
		
		if(self.entity):
			data = factory.toString(self.entity, compact=compact)
			if(data):
				return data
		
		return None
	
	def createGettyTrustGroup(self):
		"""Create the J. Paul Getty Trust Group Entity"""
		
		JPGT = Group()
		JPGT.id = "http://vocab.getty.edu/ulan/500115987"
		JPGT._label = "The J. Paul Getty Trust, Los Angeles, California"
		JPGT.classified_as = Type(ident="http://vocab.getty.edu/ulan/500000003", label="Corporate Bodies")
		
		# Return a copy of the Group so it can be modified without affecting the source
		return copy.copy(JPGT)

# Register all of the available transformers
registerTransformers()

# debug(registeredTransformers(), format="JSON")
