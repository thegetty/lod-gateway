import os
import sys
import requests
import json

# Import support for abstract classes and methods and final methods
from abcplus import ABC, abstractmethod, finalmethod

# Import our application utility functions
from app.utilities import get, has, debug, sprintf, commandOptions, isNumeric, isURL

# Import our application helper functions
from app import rewriteURL

# Import our shared Museum transformers BaseTransformer class
from app.transformers.museum import BaseTransformer as SharedMuseumBaseTransformer

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

# Abstract Museum Collection BaseTransformer class
class BaseTransformer(SharedMuseumBaseTransformer):
	
	def activityStreamEndpoint(self):
		"""Provide a method for conveying the Activity Stream endpoint that this transformer will process"""
		
		baseURL = os.getenv("MART_DOR_BASE_URL", None)
		if(isinstance(baseURL, str) and len(baseURL) > 0):
			return rewriteURL(baseURL + "/api/activity-stream/")
		else:
			raise RuntimeError("Unable to obtain MART_DOR_BASE_URL environment variable! Please check runtime environment configuration!")
		
		return None
	
	def activityStreamEndpointOptions(self):
		"""Provide a method for conveying the Activity Stream endpoint options to configure each HTTP request"""
		
		options = {}
		
		# Define our optional method to rewrite our endpoint URLs
		options["rewrite"] = BaseTransformer.activityStreamEndpointRewrite
		
		# Define the polling interval for our Activity Stream
		interval = os.getenv("MART_DOR_POLL_INTERVAL", 60)
		if(isNumeric(interval)):
			options["interval"] = int(interval)
		
		# Define the HTTP request headers needed to access our Activity Stream
		headers = self.assembleHeaders()
		if(headers):
			headers.update({
				"Accept": "application/activity+json",
			})
			
			options["headers"] = headers
		
		return options
	
	@staticmethod
	def activityStreamEndpointRewrite(URL):
		if(isinstance(URL, str) and len(URL) > 0):
			findURL = os.getenv("MART_DOR_FIND_URL", None)
			baseURL = os.getenv("MART_DOR_BASE_URL", None)
			
			return rewriteURL(URL, findURL=findURL, baseURL=baseURL)
		
		return URL
	
	@abstractmethod
	def resourceType(self):
		"""Provide a method for determining the correct target resource type name"""
		pass
	
	@finalmethod
	def assembleHeaders(self):
		"""Assemble our HTTP Request Headers for the DOR API call"""
		
		apiUser    = os.getenv("MART_DOR_API_USER", None)
		apiKey     = os.getenv("MART_DOR_API_KEY", None)
		apiVersion = os.getenv("MART_DOR_API_VERSION", None)
		
		headers = {}
		
		if(apiUser):
			if(apiKey):
				headers["Authorization"] = "ApiKey " + apiUser + ":" + apiKey
				
				if(apiVersion):
					headers["Accept"] = "application/json;charset=UTF-8;version=" + apiVersion
				else:
					raise RuntimeError("Missing DOR API Version Environment Variable!")
			else:
				raise RuntimeError("Missing DOR API Key Environment Variable!")
		else:
			raise RuntimeError("Missing DOR API User Environment Variable!")
		
		if(headers):
			# Support cache toggling from the CLI
			options = commandOptions({
				"cache": None,
			})
			
			if(options["cache"] == None and (os.getenv("MART_DOR_API_CACHING", "YES") == "NO")):
				headers["X-Request-Caching"] = "NO"
			elif(options["cache"] == False):
				headers["X-Request-Caching"] = "NO"
			
			return headers
		
		return None
	
	@finalmethod
	def generateURI(self):
		"""Generate the URI for a DOR API resource"""
		
		resource = self.resourceType()
		if(resource):
			if(self.id):
				return "/api/" + resource + "/" + str(self.id) + "/"
		else:
			raise RuntimeError("Unable to obtain a valid resource name!")
		
		return None
	
	@finalmethod
	def generateURL(self):
		"""Generate the absolute URL for a DOR API resource"""
		
		baseURL = os.getenv("MART_DOR_BASE_URL", None)
		findURL = os.getenv("MART_DOR_FIND_URL", None)
		URL     = None
		
		# If the ID has been provided as an absolute URL, use it as-is
		if(isURL(self.id)):
			URL = self.id
		else: # Otherwise, generate the URI and then prefix it to obtain the URL
			URI = self.generateURI()
			if(isinstance(URI, str) and len(URI) > 0):
				if(isinstance(baseURL, str) and len(baseURL) > 0):
					URL = baseURL + "/" + URI
				else:
					URL = URI
		
		if(isinstance(URL, str) and len(URL) > 0):
			return rewriteURL(URL, findURL=findURL, baseURL=baseURL)
		
		return None
	
	@finalmethod
	def getUUID(self):
		# debug("%s.getUUID() called..." % (self.__class__.__name__))
		
		if(self.data):
			if("uuid" in self.data):
				if(isinstance(self.data["uuid"], str)):
					return self.data["uuid"]
				else:
					debug("The current record's UUID was not a string, but of type '%s' instead!" % (type(self.data["uuid"])), error=True)
			else:
				debug("Unable to obtain the current record's UUID!", error=True)
		else:
			debug("Unable to obtain the current record's data!", error=True)
		
		return None
	
	@finalmethod
	def getData(self):
		"""Obtain the data for the specified DOR entity resource"""
		
		URL = self.generateURL()
		if(isinstance(URL, str) and len(URL) > 0):
			debug("%s.getData() Attempt to obtain: %s" % (self.__class__.__name__, URL), level=1)
			
			headers = self.assembleHeaders()
			if(isinstance(headers, dict)):
				response = requests.get(URL, headers=headers)
				if(isinstance(response, requests.models.Response)):
					if(response.status_code == 200):
						if(isinstance(response.text, str) and len(response.text) > 0):
							if((response.text.startswith("{") and response.text.endswith("}")) or (response.text.startswith("[") and response.text.endswith("]")) or response.text == "null"):
								data = json.loads(response.text)
								if(isinstance(data, dict)):
									self.id   = get(data, "id")
									self.UUID = get(data, "uuid")
									self.data = data
									
									return data
								else:
									debug("%s.getData() Invalid JSON Data!" % (self.__class__.__name__), error=True)
							else:
								debug("%s.getData() Invalid JSON String!" % (self.__class__.__name__), error=True)
						else:
							debug("%s.getData() Invalid Response Text!" % (self.__class__.__name__), error=True)
					else:
						debug("%s.getData() Invalid HTTP Response Status Code! Expected HTTP/1.1 200 OK; Received %d!" % (self.__class__.__name__, response.status_code), error=True)
				else:
					debug("%s.getData() Invalid HTTP Response!" % (self.__class__.__name__), error=True)
			else:
				debug("%s.getData() Missing HTTP Request Headers!" % (self.__class__.__name__), error=True)
		else:
			debug("%s.getData() Invalid URL!" % (self.__class__.__name__), error=True)
		
		return None
	
	@finalmethod
	def mapDigitalObjectRepositoryRecordIDs(self, entity, data):
		"""Map the record's DOR ID and UUID"""
		
		number = get(data, "id")
		if(number):
			identifier = Identifier()
			identifier.id = self.generateEntityURI(sub=["identifier", "dor-id"])
			identifier._label = "Getty Digital Object Repository (DOR) ID"
			identifier.content = number
			
			identifier.classified_as = Type(ident="http://vocab.getty.edu/internal/ontologies/linked-data/dor-identifier", label="Getty Digital Object Repository (DOR) ID")
			
			entity.identified_by = identifier
		
		number = get(data, "uuid")
		if(number):
			identifier = Identifier()
			identifier.id = self.generateEntityURI(sub=["identifier", "dor-uuid"])
			identifier._label = "Getty Digital Object Repository (DOR) UUID"
			identifier.content = number
			
			identifier.classified_as = Type(ident="http://vocab.getty.edu/internal/ontologies/linked-data/universally-unique-identifier", label="Universally Unique Identifier (UUID)")
			
			entity.identified_by = identifier
	
	@finalmethod
	def mapTheMuseumSystemRecordIDs(self, entity, data):
		"""Map the record's TMS ID"""
		
		number = get(data, "record_identifier")
		if(number):
			identifier = Identifier()
			identifier.id = self.generateEntityURI(sub=["identifier", "tms-id"])
			identifier._label = "Gallery Systems' The Museum System (TMS) ID"
			identifier.content = number
			
			identifier.classified_as = Type(ident="http://vocab.getty.edu/internal/ontologies/linked-data/tms-identifier", label="Gallery Systems' The Museum System (TMS) ID")
			
			entity.identified_by = identifier