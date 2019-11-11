import os
import sys
import requests
import json

from random import randint
from time import sleep

# Import support for abstract classes and methods
from abc import ABC, abstractmethod

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
		
		baseURL = os.getenv("DOR_BASE_URL", None)
		if(isinstance(baseURL, str) and len(baseURL) > 0):
			return rewriteURL(baseURL + "/api/activity-stream/")
		else:
			raise RuntimeError("Unable to obtain DOR_BASE_URL environment variable! Please check runtime environment configuration!")
		
		return None
	
	def activityStreamEndpointOptions(self):
		"""Provide a method for conveying the Activity Stream endpoint options to configure each HTTP request"""
		
		options = {}
		
		# Define our optional method to rewrite our endpoint URLs
		options["rewrite"] = BaseTransformer.activityStreamEndpointRewrite
		
		# Define the polling interval for our Activity Stream
		interval = os.getenv("DOR_POLL_INTERVAL", 60)
		if(isNumeric(interval)):
			options["interval"] = int(interval)
		
		retries = os.getenv("DOR_API_MAX_RETRIES", 5)
		if(isNumeric(retries)):
			options["retries"] = int(retries)
		
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
			findURL = os.getenv("DOR_FIND_URL", None)
			baseURL = os.getenv("DOR_BASE_URL", None)
			
			return rewriteURL(URL, findURL=findURL, baseURL=baseURL)
		
		return URL
	
	@abstractmethod
	def resourceType(self):
		"""Provide a method for determining the correct target resource type name"""
		pass
	
	# final method; please do not override
	def assembleHeaders(self):
		"""Assemble our HTTP Request Headers for the DOR API call"""
		
		apiUser    = os.getenv("DOR_API_USER", None)
		apiKey     = os.getenv("DOR_API_KEY", None)
		apiVersion = os.getenv("DOR_API_VERSION", None)
		
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
		
		# Support cache toggling from the CLI
		options = commandOptions({
			"cache":  None,
			"header": None,
		})
		
		if(options["cache"] == None and (os.getenv("DOR_API_CACHING", "YES") == "NO")):
			headers["X-Request-Caching"] = "NO"
		elif(options["cache"] == False):
			headers["X-Request-Caching"] = "NO"
		
		for key in os.environ:
			if(key.startswith("HTTP_HEADER_")):
				var = os.environ[key]
				if(isinstance(var, str) and len(var) > 0):
					header, value = var.split(":", 1)
					if(header and value):
						header = header.strip()
						value  = value.strip()
						
						headers[header] = value
		
		if(isinstance(options["header"], str) and len(options["header"]) > 0):
			options["header"] = [options["header"]]
		
		if(isinstance(options["header"], list) and len(options["header"]) > 0):
			for header in options["header"]:
				header, value = header.split(":", 1)
				if(header and value):
					header = header.strip()
					value  = value.strip()
					
					headers[header] = value
		
		return headers
	
	# final method; please do not override
	def generateURI(self):
		"""Generate the URI for a DOR API resource"""
		
		resource = self.resourceType()
		if(resource):
			if(self.id):
				return "/api/" + resource + "/" + str(self.id) + "/"
		else:
			raise RuntimeError("Unable to obtain a valid resource name!")
		
		return None
	
	# final method; please do not override
	def generateURL(self):
		"""Generate the absolute URL for a DOR API resource"""
		
		baseURL = os.getenv("DOR_BASE_URL", None)
		findURL = os.getenv("DOR_FIND_URL", None)
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
	
	# final method; please do not override
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
	
	# final method; please do not override
	def getData(self):
		"""Obtain the data for the specified DOR entity resource"""
		
		URL = self.generateURL()
		if(isURL(URL)):
			debug("%s.getData(%s) Attempt to Obtain URL..." % (self.__class__.__name__, URL), level=1)
			
			headers = self.assembleHeaders()
			if(isinstance(headers, dict)):
				retry   = 0;
				retries = os.getenv("DOR_API_MAX_RETRIES", 5);
				
				while(True):
					try:
						response = requests.get(URL, headers=headers, timeout=90)
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
											debug("%s.getData(%s) Invalid JSON Data!" % (self.__class__.__name__, URL), error=True)
									else:
										debug("%s.getData(%s) Invalid JSON String!" % (self.__class__.__name__, URL), error=True)
								else:
									debug("%s.getData(%s) Invalid Response Text!" % (self.__class__.__name__, URL), error=True)
							else:
								debug("%s.getData(%s) Invalid HTTP Response Status Code! Expected HTTP/1.1 200 OK; Received %d!" % (self.__class__.__name__, URL, response.status_code), error=True)
						else:
							debug("%s.getData(%s) Invalid HTTP Response!" % (self.__class__.__name__, URL), error=True)
						
						if(retry < retries):
							debug("%s.getData(%s) HTTP Request Failed! Retry Attempt %d/%d..." % (self.__class__.__name__, URL, (retry + 1), retries), error=True)
							
							sleep(randint(3, 10)) # Sleep for 3 - 10 seconds before retrying
							retry += 1
						else: # The maximum number of retries has been exceeded, so break here...
							debug("%s.getData(%s) Maximum Number of Retries (%d/%d) Reached for HTTP Request! Breaking Now!" % (self.__class__.__name__, URL, (retry + 1), retries), error=True)
							break
					except Exception as e:
						debug("%s.getData(%s) HTTP Request Raised Exception: %s!" % (self.__class__.__name__, URL, str(e)), error=True)
						break
			else:
				debug("%s.getData(%s) Missing HTTP Request Headers!" % (self.__class__.__name__, URL), error=True)
		else:
			debug("%s.getData(%s) Invalid URL!" % (self.__class__.__name__, URL), error=True)
		
		return None
	
	# final method; please do not override
	def mapDigitalObjectRepositoryRecordIDs(self, entity, data):
		"""Map the record's DOR ID and UUID"""
		
		number = get(data, "id")
		if(number):
			identifier = Identifier()
			identifier.id = self.generateEntityURI(sub=["identifier", "dor-id"])
			identifier._label = "Getty Digital Object Repository (DOR) ID"
			identifier.content = str(number)
			
			identifier.classified_as = Type(ident="https://data.getty.edu/museum/ontology/linked-data/dor/identifier", label="Getty Digital Object Repository (DOR) ID")
			
			identifier.classified_as = Type(ident="https://data.getty.edu/museum/ontology/linked-data/integer-identifier", label="Integer Identifier")
			
			entity.identified_by = identifier
		
		number = get(data, "uuid")
		if(number):
			identifier = Identifier()
			identifier.id = self.generateEntityURI(sub=["identifier", "dor-uuid"])
			identifier._label = "Getty Digital Object Repository (DOR) UUID"
			identifier.content = number
			
			identifier.classified_as = Type(ident="https://data.getty.edu/museum/ontology/linked-data/dor/identifier", label="Getty Digital Object Repository (DOR) ID")
			
			identifier.classified_as = Type(ident="https://data.getty.edu/museum/ontology/linked-data/universally-unique-identifier", label="Universally Unique Identifier (UUID)")
			
			entity.identified_by = identifier
	
	# final method; please do not override
	def mapTheMuseumSystemRecordIDs(self, entity, data):
		"""Map the record's TMS ID"""
		
		number = get(data, "record_identifier")
		if(number):
			identifier = Identifier()
			identifier.id = self.generateEntityURI(sub=["identifier", "tms-id"])
			identifier._label = "Gallery Systems' The Museum System (TMS) ID"
			identifier.content = str(number)
			
			identifier.classified_as = Type(ident="https://data.getty.edu/museum/ontology/linked-data/tms/identifier", label="Gallery Systems' The Museum System (TMS) ID")
			
			identifier.classified_as = Type(ident="https://data.getty.edu/museum/ontology/linked-data/integer-identifier", label="Integer Identifier")
			
			entity.identified_by = identifier