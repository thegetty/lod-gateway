from abc import ABC, abstractmethod

import json
import requests
import os
import re
import inspect
import copy
import sys

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

from .. utilities import get, has

# Abstract BaseRecord class for all Model (Record) entities
class BaseRecord(ABC):
	
	def __init__(self, id):
		self.className = self.__class__.__name__
		self.entity    = None
		self.id        = id
		self.resource  = None
		self.data      = None
	
	def info(self):
		print("The '%s' eneity was just initialized with: id = %s; resource = %s; uri = %s" % (self.className, str(self.id), self.resource, self.generateURI()))
	
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
			testCaching = None
			if(sys.argv):
				for index, argv in enumerate(sys.argv):
					if(argv == "--cache"):
						if(sys.argv[(index + 1)]):
							testCaching = sys.argv[(index + 1)]
			
			if(testCaching == None and (os.getenv("MART_DOR_API_CACHING", "YES") == "NO")):
				headers["X-Request-Caching"] = "NO"
			elif(testCaching == "NO"):
				headers["X-Request-Caching"] = "NO"
			
			return headers
		
		return None
	
	def generateURI(self):
		"""Generate the URI for a DOR API resource"""
		
		return "/api/" + self.resource + "/" + str(self.id) + "/"
	
	def generateURL(self):
		"""Generate the absolute URL for a DOR API resource"""
		
		baseURL   = os.getenv("MART_DOR_BASE_URL", None)
		recordURI = self.generateURI()
		
		if(baseURL):
			if(recordURI):
				return baseURL + "/" + recordURI
		
		return None
	
	def generateEntityName(self, **kwargs):
		"""Generate an hyphenated entity name for the current or provided entity for use in URIs/URLs"""
		
		entity = copy.copy(self.entity)
		
		if("entity" in kwargs):
			entity = kwargs["entity"]
		
		if(entity):
			# If the passed entity is a type, not an object
			if(isinstance(entity, type)):
				# Instantiate it so that we can correctly determine its class name
				entity = entity()
			
			if(entity.__class__):
				if(entity.__class__.__name__):
					className = entity.__class__.__name__
					
					# Split the entity name on upper case characters
					parts = re.findall("[A-Z][^A-Z]*", className)
					if(parts and len(parts) > 0):
						# Lowercase each part of the entity name
						for index, part in enumerate(parts):
							parts[index] = part.lower()
						
						# Hyphenate the parts for readability
						return "-".join(parts)
		
		return None
	
	def generateEntityURI(self, **kwargs):
		"""Generate an entity URI for the current or provided entity"""
		
		baseURL = os.getenv("MART_LOD_BASE_URL");
		
		if(self.data):
			if("uuid" in self.data):
				UUID = self.data["uuid"]
				
				if("UUID" in kwargs):
					if(isinstance(kwargs["UUID"], str)):
						UUID = kwargs["UUID"]
				
				if(self.entity):
					entity = self.entity
					
					if("entity" in kwargs):
						entity = kwargs["entity"]
					
					# print("UUID = %s; entity = %s" % (UUID, entity))
					
					entityName = self.generateEntityName(entity=entity);
					if(entityName):
						ID = baseURL + "/" + entityName + "/" + UUID + "/";
						
						if("sub" in kwargs):
							if(len(kwargs["sub"]) > 0):
								ID += "/".join(kwargs["sub"]) + "/";
						
						return ID
					else:
						raise RuntimeError("Missing CROM entity name!")
				else:
					raise RuntimeError("Missing CROM entity representation!")
			else:
				raise RuntimeError("Missing record UUID!")
		else:
			raise RuntimeError("Missing record data!")
		
		return None
	
	def getData(self):
		"""Obtain the data for the specified DOR entity resource"""
		
		URL = self.generateURL();
		
		if(URL):
			headers = self.assembleHeaders()
			if(headers):
				response = requests.get(URL, headers=headers)
				if(response):
					if(response.status_code == 200):
						data = json.loads(response.text)
						if(data):
							self.data = data
							
							return True
						else:
							raise RuntimeError("Invalid JSON Data!")
					else:
						raise RuntimeError("Invalid HTTP Response Status Code!")
				else:
					raise RuntimeError("Invalid HTTP Response!")
			else:
				raise RuntimeError("Missing DOR API Version Environment Variable!")
		else:
			raise RuntimeError("Missing DOR API Version Environment Variable!")
		
		return False
	
	@abstractmethod
	def entityType(self):
		"""Provide a method for determining the correct target entity type"""
		
		pass
	
	def mapData(self):
		"""Orchestrate the data mapping process"""
		
		# Create entity instance
		entityType = self.entityType()
		if(entityType):
			entity = entityType()
			if(entity):
				self.entity = entity
				
				# Assign entity ID
				self.entity.id = self.generateEntityURI();
				
				# For testing, support specifying and running a specified method from the CLI
				testMethod = None
				if(sys.argv):
					for index, argv in enumerate(sys.argv):
						if(argv == "--method"):
							if(sys.argv[(index + 1)]):
								testMethod = sys.argv[(index + 1)]
				
				# Now look for any class methods starting with the word "map";
				# we will then call any of the discovered "map" methods to update
				# the entity instance by mapping part of the data; we exclude
				# any calls to the "mapData" method below to prevent infinite recursion
				methods = inspect.getmembers(self, predicate=inspect.ismethod);
				for method in methods:
					if(method and method[0]):
						methodName = method[0];
						if(isinstance(methodName, str)):
							if(methodName.startswith("map")):
								if(methodName not in ["mapData"]):
									mapMethod = getattr(self, methodName)
									if(mapMethod):
										# Run all methods if no test has been defined, or just the matching method
										if((testMethod == None) or (testMethod == methodName)):
											# As "self.entity" is passed by reference, it may be
											# updated directly by the called "map" method
											mapMethod(self.entity, self.data)
				
				if(entity):
					return entity
				else:
					raise RuntimeError("Failed to Map CROM Entity () Instance!")
			else:
				raise RuntimeError("Failed to Instantiate CROM Entity () Instance!")
		else:
			raise RuntimeError("Failed to Obtain CROM Entity Type!")
		
		return None
	
	def toJSON(self):
		"""Convert the mapped data into its JSON-LD serialization using CROM's Factory.toString() method"""
		
		if(self.entity):
			data = factory.toString(self.entity, compact=False)
			if(data):
				return data
		
		return None
	
	# Create J. Paul Getty Trust Group Entity
	def createGettyTrustGroup(self):
		JPGT = Group()
		JPGT.id = "http://vocab.getty.edu/ulan/500115987"
		JPGT._label = "J. Paul Getty Trust, Los Angeles, California"
		JPGT.classified_as = Type(ident="http://vocab.getty.edu/ulan/500000003", label="Corporate Bodies")
		
		# Return a copy of the Group so it can be modified without affecting the source
		return copy.copy(JPGT)
	
	# Create J. Paul Getty Museum Group Entity
	def createGettyMuseumGroup(self):
		JPGT = self.createGettyTrustGroup()
		
		JPGM = Group()
		JPGM.id = "http://vocab.getty.edu/ulan/500115988"
		JPGM._label = "J. Paul Getty Museum, Los Angeles, California"
		JPGM.classified_as = Type(ident="http://vocab.getty.edu/aat/300312281", label="Museum")
		
		# Note that the Museum is a "member_of" (part of) the Trust
		JPGM.member_of = JPGT
		
		# Return a copy of the Group so it can be modified without affecting the source
		return copy.copy(JPGM)
