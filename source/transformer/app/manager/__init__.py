import json
import requests
import os
import re
import inspect
import copy
import sys
import re

from random import randint
from time import sleep

# Import support for abstract classes and methods
from abc import ABC, abstractmethod

# Import our application dependency injector (DI)
from app.di import DI

# Import our application utility functions
from app.utilities import get, has, debug

# Import our shared application helper functions
from app import *

# Import our shared transformer helper functions
from app.transformers import *

# Import our shared data model classes
from app.model import Activity, Stream, Record
from app.graph import GraphStore

# Abstract BaseManager class for all Manager entities
class BaseManager(ABC):
	
	transformers = None
	
	def __init__(self):
		self.transformers = registeredTransformers()
	
	@abstractmethod
	def process(self, **kwargs):
		pass
	
	# final method; please do not override
	def getSourceData(self, URL=None, options=None):
		"""Provide support for calling a URL and obtaining its (expected) JSON response body"""
		
		debug("%s.getData(URL: %s) called..." % (self.__class__.__name__, URL), level=1)
		
		if(not (isinstance(URL, str) and len(URL) > 0)):
			debug("%s.getData(URL: %s) The provided URL was invalid!" % (self.__class__.__name__, URL), error=True)
			return None
		
		headers = None
		
		if(isinstance(options, dict)):
			# if a URL rewrite method has been provided, rewrite the provided URL
			if("rewrite" in options and callable(options["rewrite"])):
				URL = options["rewrite"](URL)
			elif(isCallable(self, "sourceDataURL")):
				URL = self.sourceDataURL(URL)
			
			# if any HTTP request headers have been provided
			if("headers" in options):
				if(isinstance(options["headers"], dict)):
					# obtain them for use below
					headers = options["headers"]
				elif(isCallable(self, "sourceDataHeaders")):
					headers = self.sourceDataHeaders()
		
		# debug(options, format="JSON", label="options")
		# debug(headers, format="JSON", label="headers")
		
		try:
			response = requests.get(URL, headers=headers, timeout=90)
			if(isinstance(response, requests.models.Response)):
				if(response.status_code == 200):
					data = response.text
					
					if("process" in options and callable(options["process"])):
						data = options["process"](data, response=response)
					elif(callable(getattr(self, "processSourceData", None))):
						data = self.processSourceData(data, response=response)
					else:
						debug("No source data processor found!", error=True)
					
					return data
				else:
					debug("%s.getData(URL: %s) The response status code was invalid; expected HTTP/1.1 200 OK, instead received %s!" % (self.__class__.__name__, URL, response.status_code), error=True)
					# debug(dir(response))
					# debug(response.request.headers, label="response.request.headers")
					# debug(response.headers, label="response.headers")
					# debug(json.loads(response.text), format="JSON", label="\nresponse.text:\n")
			else:
				debug("%s.getData(URL: %s) The response (%s) was invalid!" % (self.__class__.__name__, URL, type(response)), error=True)
		except Exception as e:
			debug("%s.getData(URL: %s) The request resulted in an exception being thrown: %s!" % (self.__class__.__name__, URL, str(e)), error=True)
		
		return None
	
	def processSourceData(self, data, response=None):
		return data
	
	# final method; please do not override
	def processItem(self, item, **kwargs):
		debug("%s.processItem(item: %s) called..." % (self.__class__.__name__, item), level=1)
		
		response = None
		
		options = commandOptions({
			"output": None, # output destination for generated/transformed records? (default: database, when not set)
		})
		
		if(isinstance(item, dict)):
			event     = get(item, "event")
			namespace = get(item, "namespace")
			entity    = get(item, "entity")
			id        = get(item, "id")
			
			transformerClass = transformerForEntity(entity=entity, namespace=namespace)
			if(transformerClass):
				entity = transformerClass(id=id)
				if(entity):
					if(entity.getData()):
						entitySpace = entity.getNamespace()
						if(not entitySpace):
							raise RuntimeError("Unable to obtain transformer's namespace!")
						
						entityName = entity.getEntityName()
						if(not entityName):
							raise RuntimeError("Unable to obtain transformer's entity name!")
						
						entityUUID = entity.getUUID()
						if(not entityUUID):
							raise RuntimeError("Unable to obtain transformer's entity UUID!")
						
						if(entity.mapData()):
							# Determine JSON Output Formatting
							if(options["output"]):
								compact = False
							else:
								compact = True
							
							# Serialize the transformed data to JSON-LD
							data = entity.toJSON(compact=compact)
							if(data):
								if(options["output"] == "debug"):
									debug(data)
								elif(options["output"] == "file"):
									file = os.path.abspath("/usr/local/mart/data/transformer/" + entitySpace + "/" + entityName + "/" + entityUUID + ".json")
									path = os.path.dirname(file)
									try:
										os.makedirs(path, exist_ok=True)
										
										with open(file, "w+") as handle:
											handle.write(data)
									except:
										debug("An exception occurred while trying to create the output directory path or write to a file!", error=True)
								else:
									if(self.storeEntity(entity, data=data)):
										debug("Successfully saved %s..." % (entity), level=1)
										debug("This record will be available via the web service at: %s" % (entity.generateEntityURI()), indent=1)
										
										response = True
									else:
										debug("Failed to save %s!" % (entity), error=True)
										
										response = False
							else:
								debug("%s.processItem() Unable to serialize data for specified item: %s!" % (self.__class__.__name__, item), error=True)
						else:
							debug("%s.processItem() Unable to map data for specified item: %s!" % (self.__class__.__name__, item), error=True)
					else:
						debug("%s.processItem() Unable to obtain data for specified item: %s!" % (self.__class__.__name__, item), error=True)
				else:
					debug("%s.processItem() Unable to instantiate transformer class for specified item: %s!" % (self.__class__.__name__, item), error=True)
			else:
				debug("%s.processItem() Unable to determine transformer class for specified item: %s!" % (self.__class__.__name__, item), error=True)
		else:
			debug("%s.processItem() Provided item was not a dictionary as expected, but rather of type: %s" % (self.__class__.__name__, type(item)), error=True)
		
		return response
	
	# final method; please do not override
	def storeEntity(self, entity, data=None, **kwargs):
		debug("%s.storeEntity(entity: %s, kwargs: %s) called..." % (self.__class__.__name__, entity, kwargs), level=1)
		
		if(not entity):
			debug("%s.storeEntity() The 'entity' parameter was invalid!" % (self.__class__.__name__), error=True)
			return False
		
		namespace  = self.getEntityNamespace(entity, **kwargs)
		entityName = self.getEntityName(entity, **kwargs)
		entityUUID = self.getEntityUUID(entity, **kwargs)
		entityURI  = self.getEntityURI(entity, **kwargs)
		
		if(not namespace):
			debug("%s.storeEntity() The 'namespace' parameter was invalid!" % (self.__class__.__name__), error=True)
			return False
		
		if(not entityName):
			debug("%s.storeEntity() The 'entityName' parameter was invalid!" % (self.__class__.__name__), error=True)
			return False
		
		if(not entityUUID):
			debug("%s.storeEntity() The 'UUID' parameter was invalid!" % (self.__class__.__name__), error=True)
			return False
		
		if(not entityURI):
			entityURI = BaseTransformer.assembleEntityURI(namespace=namespace, entityName=entityName, UUID=UUID)
		
		if(entity.__module__ == "cromulent.model" and not entity.id):
			entity.id = entityURI
		
		debug({
			"namespace":  namespace,
			"entityName": entityName,
			"entityUUID": entityUUID,
			"entityURI":  entityURI,
		}, format="JSON", level=2)
		
		if(data == None):
			if(isinstance(entity, BaseTransformer)):
				data = entity.toJSON(compact=True)
			else:
				if("compact" in kwargs and isinstance(kwargs["compact"], bool)):
					compact = kwargs["compact"]
				else:
					compact = True
				
				data = factory.toString(entity, compact=compact)
		
		record = Record.findFirstOrCreateNewInstance("namespace = :namespace: AND entity = :entity: AND uuid = :uuid:", bind={"namespace": namespace, "entity": entityName, "uuid": entityUUID})
		if(record):
			record.namespace = namespace
			record.entity    = entityName
			record.uuid      = entityUUID
			record.data      = data
			
			if(record.save()):
				debug("Successfully saved %s" % (record), level=2)
				
				if(GraphStore.update(entityURI, record.data)):
					record.commit()
				else:
					debug("Failed to update %s within the graph store!" % (record), error=True)
					
					record.rollback()
					return False
				
				return True
			else:
				debug("Failed to save %s!" % (record), error=True)
				
				record.rollback()
		else:
			debug("Failed to find or create a Record instance for %s!" % (entity), error=True)
		
		return False
	
	# final method; please do not override
	def getEntityNamespace(self, entity, **kwargs):
		namespace = None
		
		if("namespace" in kwargs):
			namespace = kwargs["namespace"]
		else:
			if(isinstance(entity, BaseTransformer)):
				namespace = entity.getNamespace()
			elif(entity.__module__ == "cromulent.model" and getattr(entity, "_namespace", None)):
				namespace = entity._namespace
				del entity._namespace
		
		return namespace
	
	# final method; please do not override
	def getEntityName(self, entity, **kwargs):
		debug("%s.getEntityName(%s, %s) called..." % (self.__class__.__name__, entity, kwargs))
		
		name = None
		
		if("name" in kwargs):
			name = kwargs["name"]
		elif("entityName" in kwargs):
			name = kwargs["entityName"]
		else:
			if(isinstance(entity, BaseTransformer)):
				name = entity.getEntityName()
			elif(entity.__module__ == "cromulent.model"):
				if(getattr(entity, "_name", None)):
					name = entity._name
					del entity._name
				else:
					name = entity.__class__.__name__
		
		return name
	
	# final method; please do not override
	def getEntityUUID(self, entity, **kwargs):
		UUID = None
		
		if("UUID" in kwargs):
			UUID = kwargs["UUID"]
		else:
			if(isinstance(entity, BaseTransformer)):
				UUID = entity.getUUID()
			elif(entity.__module__ == "cromulent.model" and getattr(entity, "_uuid", None)):
				UUID = entity._uuid
				del entity._uuid
		
		return UUID
	
	# final method; please do not override
	def getEntityURI(self, entity, **kwargs):
		entityURI = None
		
		if("entityURI" in kwargs):
			entityURI = kwargs["entityURI"]
		else:
			if(isinstance(entity, BaseTransformer)):
				entityURI = entity.generateEntityURI()
			elif(entity.__module__ == "cromulent.model" and getattr(entity, "id", None)):
				entityURI = entity.id
		
		return entityURI

class ActivityStreamManager(BaseManager):
	
	def process(self, **kwargs):
		if(has(kwargs, "namespace") and has(kwargs, "entity") and has(kwargs, "id")):
			self.processItem(**kwargs)
		else:
			self.processStreams()
	
	def processSourceData(self, data, response=None):
		debug("%s.processActivityStreams(data: %s, response: %s) called..." % (self.__class__.__name__, data, response), level=1)
		
		if(data):
			return json.loads(data)
		
		return None
	
	def processStreams(self):
		"""Process the registered Activity Streams and convert any referenced items of interest"""
		
		debug("BaseManager.processActivityStreams() called...", level=1)
		
		direction = None
		
		options = commandOptions({
			"direction": None,
		})
		
		if("direction" in options):
			if(isinstance(options["direction"], str)):
				if(options["direction"] in ["first", "current", "last"]):
					direction = options["direction"]
		
		# Obtain the list of registered transformers
		transformers = registeredTransformers()
		if(isinstance(transformers, dict) and len(transformers) > 0):
			endpoints = {}
			
			# Organise our transformers by stream endpoints, so we can process streams holistically
			for namespace in transformers:
				for transformer in transformers[namespace]:
					if(isinstance(transformer, dict)):
						endpoint = get(transformer, "stream.endpoint")
						if(isinstance(endpoint, str)):
							types = get(transformer, "stream.types")
							if(isinstance(types, list) and len(types) > 0):
								options = get(transformer, "stream.options")
								
								if(endpoint in endpoints):
									endpoints[endpoint]["transformers"].append(transformer)
								else:
									endpoints[endpoint] = {
										"namespace":    namespace,
										"options":      options,
										"transformers": [transformer],
									}
			
			# Assuming we built a suitable dictionary of endpoints
			if(isinstance(endpoints, dict) and len(endpoints) > 0):
				debug("Found %d Activity Stream endpoints to process..." % (len(endpoints)), indent=1, level=2)
				# debug(endpoints, format="JSON")
				
				# Proceed to iterate over and process each Activity Stream endpoint
				for endpoint in endpoints:
					data = endpoints[endpoint]
					if(isinstance(data, dict)):
						debug("Processing Activity Stream endpoint: %s for namespace: %s" % (endpoint, namespace), indent=2, level=2)
						
						self.processStream(URL=endpoint, namespace=data["namespace"], transformers=data["transformers"], options=data["options"], direction=direction)
			else:
				raise RuntimeError("Failed to assemble set of Activity Stream endpoints for processing!")
		else:
			raise RuntimeError("Failed to obtain any registered transformers!")
		
		return
	
	def processStream(self, URL=None, namespace=None, transformers=None, options=None, direction=None):
		"""Process the registered Activity Streams and convert any referenced items of interest"""
		
		debug("BaseManager.processActivityStream(URL: %s, namespace: %s, direction: %s) called..." % (URL, namespace, direction), level=1)
		
		if(not (isinstance(URL, str) and len(URL) > 0)):
			raise RuntimeError(sprintf("Missing Activity Stream URL! Expected a string, found %s instead!" % (type(URL))))
		
		if(not (isinstance(namespace, str) and len(namespace) > 0)):
			raise RuntimeError(sprintf("Missing Activity Stream Namespace! Expected a string, found %s instead!" % (type(namespace))))
		
		if(not (isinstance(transformers, list) and len(transformers) > 0)):
			raise RuntimeError(sprintf("Missing Activity Stream Transformers! Expected a list, found %s instead!" % (type(transformers))))
		
		eventTypes = [
			"Create",
			"Update",
			"Delete",
		]
		
		lastID = None
		stream = Stream.findFirstOrCreateNewInstance("namespace = :namespace: and base_url = :base_url:", bind={"namespace": namespace, "base_url": URL})
		if(stream):
			if(isinstance(stream.last_id, str) and len(stream.last_id) > 0):
				lastID = stream.last_id
		
		# Iterate through each activity stream item
		for item in self.getStreamItems(URL=URL, options=options, direction=direction):
			if(item):
				if(isinstance(item, dict)):
					itemID = get(item, "id")
					if(isinstance(itemID, str) and len(itemID) > 0):
						if(isinstance(lastID, str) and (lastID == itemID)):
							debug("BaseManager.processActivityStream(URL: %s, namespace: %s, direction: %s) The current ID (%s) has been seen before... breaking now..." % (URL, namespace, direction, itemID), level=1)
							
							break
						
						# Obtain the change event type; will be one of "Create", "Update", "Delete" (stored under "type")
						eventType = get(item, "type")
						if(isinstance(eventType, str) and eventType in eventTypes):
							# Obtain the related record's URL (stored under "object" -> "id")
							recordURL = get(item, "object.id")
							if(isinstance(recordURL, str) and len(recordURL) > 0):
								# Obtain the related record's type (stored under "object" -> "type")
								recordType = get(item, "object.type")
								if(isinstance(recordType, str) and len(recordType) > 0):
									debug("ActivityStream Type: %s (%s)" % (recordType, recordURL))
									
									# Iterate through the available transformers
									for transformer in transformers:
										if(isinstance(transformer, dict)):
											# Obtain the Activity Stream record types that the current transformer supports
											streamTypes = get(transformer, "stream.types")
											# If the current transformer supports converting the current type
											if(isinstance(streamTypes, list)):
												if(recordType in streamTypes):
													debug("Found a matching transformer class supporting types: %s for this namespace: %s" % (streamTypes, namespace), level=2)
													# debug(transformer)
													
													self.processItem({
														"event":     eventType,
														"namespace": namespace,
														"entity":    recordType,
														"id":        recordURL,
													})
													
													# Obtain a reference to the current transformer's class
													# transformerClass = get(transformer, "module.class")
													# if(transformerClass):
													# 	Instantiate an instance of the relevant transformer class
													# 	entity = transformerClass(URL=recordURL)
													# 	if(entity):
													# 		if(isinstance(entity, BaseTransformer)):
													# 			obtain the record's data
													# 			data = entity.getData()
													# 			if(isinstance(data, dict)):
													# 				UUID = entity.getUUID()
													# 				check that the record's UUID was found
													# 				if(isinstance(UUID, str)):
													# 					map the record's data
													# 					if(entity.mapData()):
													# 						entityName = entity.generateEntityName()
													# 						check that the record's entity name is available
													# 						if(isinstance(entityName, str)):
													# 							serialize the record's data to JSON-LD
													# 							data = entity.toJSON(compact=True)
													# 							if(isinstance(data, str) and len(data) > 0):
													# 								debug(json.loads(data), format="JSON")
													# 								
													# 								if(self.storeEntity(entity)):
													# 									debug("Successfully stored %s..." % (entity))
													# 								else:
													# 									debug("Failed to store %s!" % (entity), error=True)
													# 							else: # unable to serialize the current record's mapped data
													# 								pass
													# 						else: # unable to obtain the current record's entity name
													# 							pass
													# 					else: # unable to map the current record's data
													# 						pass
													# 				else: # unable to obtain the current record's UUID
													# 					pass
													# 			else: # the current transformer class instance was unable to obtain any data
													# 				pass
													# 		else: # transformer class does not have the expected class hierarchy
													# 			pass
													# 	else: # failed to instantiate transformer class
													# 		debug("BaseManager.processActivityStream() Unable to obtain class instance for the current transformer!", error=True)
													# else: # invalid/missing transformer class
													# 	debug("BaseManager.processActivityStream() Unable to obtain class instance for the current transformer!", error=True)
												else: # recordType was not found in streamTypes list
													pass # not an error, just information
											else: # invalid streamTypes
												debug("BaseManager.processActivityStream() The current transformer stream types list was invalid! It must be a list instance, but was of type '%s' instead!" % (type(streamTypes)), error=True)
										else: # invalid transformer
											debug("BaseManager.processActivityStream() The current transformer was invalid! It must be a dictionary (dict) instance, but was of type '%s' instead!" % (type(transformer)), error=True)
									# end for loop for transformers
									
									if(stream):
										stream.namespace = namespace
										stream.base_url  = URL
										stream.last_id   = itemID
										
										if(stream.save()):
											debug("BaseManager.processActivityStream() Successfully updated the %s record to note the last processed item ID (%s)..." % (stream, itemID))
											
											stream.commit()
										else:
											debug("BaseManager.processActivityStream() Failed to update the %s record to note the last processed item ID (%s)!" % (stream, itemID), error=True)
											
											stream.rollback()
								else: # invalid recordType
									debug("BaseManager.processActivityStream() The current Activity Stream record type was invalid! It must be a string, but was of type '%s' instead!" % (type(recordType)), error=True)
							else: # invalid recordURL
								debug("BaseManager.processActivityStream() The current Activity Stream record URL was invalid! It must be a string, but was of type '%s' instead!" % (type(recordURL)), error=True)
						else: # invalid eventType
							debug("BaseManager.processActivityStream() The current Activity Stream event type (%s) was invalid! It must be a string and be one of the following: %s!" % (type(eventType), eventTypes), error=True)
					else: # invalid itemID
						debug("BaseManager.processActivityStream() The current Activity Stream item ID (%s) was invalid! It must be a non-empty string!" % (type(itemID)), error=True)
				else: # invalid item
					debug("BaseManager.processActivityStream() The current Activity Stream item was invalid! It must be a dictionary (dict) instance!", error=True)
		# end for loop for activity stream items
	
	def getStreamItems(self, URL=None, options=None, direction=None):
		"""Interface with the Activity Stream and yield each referenced item"""
		
		debug("BaseManager.getActivityStreamItems(URL: %s, direction: %s) called..." % (URL, direction), level=1)
		
		if(not (isinstance(URL, str) and len(URL) > 0)):
			raise RuntimeError(sprintf("No valid Activity Stream URL was provided! URL was of type %s instead of being a non-empty string!" % (type(URL))))
		
		if(isinstance(options, dict)):
			if("direction" in options):
				if(isinstance(options["direction"], str) and options["direction"] in ["first", "current", "last"]):
					direction = options["direction"]
		
		# If no valid Activity Streams direction has been specified, default to "last"
		if(not (isinstance(direction, str) and direction in ["first", "current", "last"])):
			direction = "last"
		
		# Obtain the initial Activity Streams endpoint, from which the directional page URLs
		# will be available so long as the Activity Stream conforms to the v2.0 specification
		data = self.getSourceData(URL, options=options)
		if(data):
			dataType = get(data, "type")
			if(dataType == "OrderedCollection"):
				totalItems = get(data, "totalItems", default=0)
				if(totalItems > 0):
					debug("Found %d total items..." % (totalItems), level=2)
					
					pageURL = None
					if(direction == "first" or direction == "forward"):
						pageURL = get(data, "first.id")
					elif(direction == "last" or direction == "backward"):
						pageURL = get(data, "last.id")
					elif(direction == "current"):
						pageURL = get(data, "current.id")
					
					retry   = 0
					retries = get(options, "retries", os.getenv("ACTIVITY_STREAM_MAX_RETRIES", 3))
					
					while(True):
						if(pageURL):
							debug("Ready to call: %s" % (pageURL), level=2)
							
							data = self.getSourceData(pageURL, options=options)
							if(data):
								retry = 0
								items = get(data, "orderedItems")
								if(items and len(items) > 0):
									for item in items:
										yield item
									
									# pass
								else:
									debug("BaseManager.getActivityStreamItems() No items for %s!" % (pageURL), error=True)
									break
								
								if(direction == "first"):
									pageURL = get(data, "next.id")
								elif(direction == "last"):
									pageURL = get(data, "prev.id")
								elif(direction == "current"):
									pageURL = get(data, "current.id")
								else:
									pageURL = None
							else: # no data
								debug("BaseManager.getActivityStreamItems() No data for %s!" % (pageURL), error=True)
								
								if(retry < retries):
									sleep(randint(3, 10)) # Sleep for 3 - 10 seconds before retrying
									retry += 1
								else: # The maximum number of retries has been exceeded, so break here...
									debug("BaseManager.getActivityStreamItems() Maximum Number of Retries (%d/%d) Reached for Activity Stream Page URL: %s! Breaking Now!" % ((retry + 1), retries, pageURL), error=True)
									break
						else: # no valid page URL
							debug("BaseManager.getActivityStreamItems() No valid page URL!", error=True)
							break
				else:
					debug("BaseManager.getActivityStreamItems() No items were found in the OrderedCollection for %s!" % (URL), error=True)
			else:
				debug("BaseManager.getActivityStreamItems() The expected response data type of OrderedCollection was not found for %s!" % (URL), error=True)
		else:
			debug("BaseManager.getActivityStreamItems() No data could be obtained for %s!" % (URL), error=True)
		
		yield None

class RecordsManager(BaseManager):
	
	def process(self, **kwargs):
		debug("%s.process() called..." % (self.__class__.__name__), level=1)
		
		if("id" in kwargs):
			if(not "namespace" in kwargs):
				debug("When using the manual records manager, one must also specify a valid namespace via the --namespace flag!", error=True)
				exit()
			
			if(not "entity" in kwargs):
				debug("When using the manual records manager, one must also specify a valid entity name via the --entity flag!", error=True)
				exit()
		
		self.processItems(**kwargs)
	
	def processItems(self, **kwargs):
		debug("%s.processItems() called..." % (self.__class__.__name__), level=1)
		
		for item in self.getItems(**kwargs):
			if(isinstance(item, dict)):
				self.processItem(item)
	
	def getItems(self, **kwargs):
		"""Interface with the data source and yield each referenced item"""
		
		debug("%s.getItems() called..." % (self.__class__.__name__), level=1)
		
		if("id" in kwargs):
			ids = kwargs["id"]
			if(isinstance(ids, str) and len(ids) > 0):
				if(ids.startswith("/")):
					if(os.path.isfile(ids)):
						_ids = []
						with open(ids, "r") as handle:
							line = handle.readline()
							while line:
								_ids.append(line.strip("\n"))
								
								line = handle.readline()
						ids = _ids
					else:
						debug("Invalid ID file (%s) path!" % (ids), error=True)
				else:
					ids = [ids]
			elif(isinstance(ids, int)):
				ids = [ids]
			
			if(isinstance(ids, list) and len(ids) > 0):
				event     = get(kwargs, "event", "Created")
				namespace = get(kwargs, "namespace")
				entity    = get(kwargs, "entity")
				
				for id in ids:
					debug("%s.getItems() ID = %s" % (self.__class__.__name__, id), level=1)
					
					yield {
						"event":     event,
						"namespace": namespace,
						"entity":    entity,
						"id":        id,
					}
			else:
				debug("%s.getItems() No IDs provided!" % (self.__class__.__name__), error=True)
		else:
			pass
		
		yield None
