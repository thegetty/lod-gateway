from abc import ABC, abstractmethod

import json
import requests
import os
import re
import inspect
import copy
import sys
import re

from .. utilities import get, has, debug
from .. database import Database
from .. import *
 
from .. transformers.museum.collection.record.BaseRecord import BaseRecord
from .. transformers.museum.collection.record.ArtifactRecord import ArtifactRecord
from .. transformers.museum.collection.record.ConstituentRecord import ConstituentRecord
from .. transformers.museum.collection.record.ExhibitionRecord import ExhibitionRecord
from .. transformers.museum.collection.record.GalleryRecord import GalleryRecord
from .. transformers.museum.collection.record.LocationRecord import LocationRecord

# Abstract BaseManager class for all Manager entities
class BaseManager(ABC):
	
	def __init__(self):
		self.resource   = None
		self.data       = None
		self.database   = Database()
		
		if(self.database):
			if(self.database.connection):
				pass
			else:
				debug("BaseManager.__init__() Failed to connect to the database!", error=True)
				
				raise RuntimeError("Failed to connect to the database!")
		else:
			debug("BaseManager.__init__() Failed to instantiate Database class!", error=True)
			
			raise RuntimeError("Failed to instantiate Database class!")
	
	def assembleHeaders(self, headers={}):
		"""Assemble our HTTP Request Headers for the DOR API call"""
		
		apiUser    = os.getenv("MART_DOR_API_USER", None)
		apiKey     = os.getenv("MART_DOR_API_KEY", None)
		apiVersion = os.getenv("MART_DOR_API_VERSION", None)
		
		_headers = {}
		
		if(apiUser):
			if(apiKey):
				_headers["Authorization"] = "ApiKey " + apiUser + ":" + apiKey
				
				if(apiVersion):
					_headers["Accept"] = "application/json;charset=UTF-8;version=" + apiVersion
				else:
					raise RuntimeError("Missing DOR API Version Environment Variable!")
			else:
				raise RuntimeError("Missing DOR API Key Environment Variable!")
		else:
			raise RuntimeError("Missing DOR API User Environment Variable!")
		
		if(_headers):
			# Support cache toggling from the CLI
			testCaching = None
			
			if(sys.argv):
				for index, argv in enumerate(sys.argv):
					if(argv == "--cache"):
						if(sys.argv[(index + 1)]):
							testCaching = sys.argv[(index + 1)]
			
			if(testCaching == None and (os.getenv("MART_DOR_API_CACHING", "YES") == "NO")):
				_headers["X-Request-Caching"] = "NO"
			elif(testCaching == "NO"):
				_headers["X-Request-Caching"] = "NO"
			
			if(headers and len(headers) > 0):
				for index, key in enumerate(headers):
					_headers[key] = headers[key]
			
			return _headers
		
		return None
	
	def generateURI(self, activityStream=False):
		"""Generate the URI for a DOR API resource"""
		
		if(activityStream):
			if(isinstance(self.resource, str)):
				return "/api/activity-stream/" + self.resource + "/"
			else:
				return "/api/activity-stream/"
		
		return "/api/" + self.resource + "/"
	
	def generateURL(self, activityStream=False, **kwargs):
		"""Generate the absolute URL for a DOR API resource list endpoint"""
		
		baseURL   = os.getenv("MART_DOR_BASE_URL", None)
		recordURI = self.generateURI(activityStream=activityStream)
		
		if(baseURL):
			if(recordURI):
				URL = baseURL + "/" + recordURI
				
				if(kwargs and len(kwargs) > 0):
					parameters = []
					
					for index, key in enumerate(kwargs):
						parameters.append(key + "=" + str(kwargs[key]))
					
					if(len(parameters) > 0):
						URL += "?" + "&".join(parameters)
				
				# replace any instances of "//" with "/" except "://"
				URL = re.sub(r'(?<!:)//', "/", URL)
				
				return URL
		
		return None
	
	def getResponse(self, URL=None, headers=None):
		if(URL):
			URL = transformURL(URL)
			
			if(headers == None):
				headers = {
					"X-Request-Envelope": "NO", # disable the envelope
				}
			
			headers = self.assembleHeaders(headers)
			
			if(headers):
				response = requests.get(URL, headers=headers)
				if(response):
					if(response.status_code == 200):
						data = json.loads(response.text)
						if(data):
							return data
		
		return False
	
	def getIDs(self, offset=0, limit=100):
		URL = self.generateURL(offset=offset, limit=limit, fields="(id)")
		
		data = self.getResponse(URL)
		if(data):
			return data
		
		return False
	
	def getActivityStreamItems(self, direction=None):
		"""Interface with the DOR's Activity Stream and yield each referenced item"""
		
		URL = self.generateURL(activityStream=True)
		
		debug("BaseManager.getActivityStreamItems() Ready to call: %s" % (URL))
		
		data = self.getResponse(URL)
		if(data):
			type = get(data, "type")
			if(type == "OrderedCollection"):
				totalItems = get(data, "totalItems", default=0)
				if(totalItems > 0):
					debug("Found %d total items..." % (totalItems))
					
					pageURL = None
					if(direction == "first" or direction == "forward"):
						pageURL = get(data, "first.id")
					elif(direction == "last" or direction == "backward"):
						pageURL  = get(data, "last.id")
					elif(direction == "current"):
						pageURL  = get(data, "current.id")
					
					while(True):
						if(pageURL):
							debug("Ready to call: %s" % (pageURL))
							
							data = self.getResponse(pageURL)
							if(data):
								items = get(data, "orderedItems")
								if(items and len(items) > 0):
									for item in items:
										yield item
									
									# pass
								else:
									debug("BaseManager.getActivityStreamItems() No items for %s!" % (pageURL), error=True, level=-1)
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
								debug("BaseManager.getActivityStreamItems() No data for %s!" % (pageURL), error=True, level=-1)
								break
						else: # no valid page URL
							debug("BaseManager.getActivityStreamItems() No valid page URL!", error=True, level=-1)
							break
				else:
					debug("BaseManager.getActivityStreamItems() No items were found in the OrderedCollection for %s!" % (URL), error=True, level=-1)
			else:
				debug("BaseManager.getActivityStreamItems() The expected response data type of OrderedCollection was not found for %s!" % (URL), error=True, level=-1)
		else:
			debug("BaseManager.getActivityStreamItems() No data could be obtained for %s!" % (URL), error=True, level=-1)
		
		yield None
	
	def processActivityStream(self, direction=None):
		"""Process the DOR's Activity Stream and convert any referenced items of interest"""
		
		debug("BaseManager.processActivityStream(direction: %s) called..." % (direction))
		
		# iterate through each activity stream item
		for item in self.getActivityStreamItems(direction=direction):
			# debug(item, format="JSON")
			
			if(item is not None):
				if(isinstance(item, dict)):
					# obtain the change event type; will be one of "Create", "Update", "Delete" (stored under "type")
					event = get(item, "type")
					if(isinstance(event, str)):
						# obtain the related record's URL (stored under "object" -> "id")
						recordURL = transformURL(get(item, "object.id"))
						if(isinstance(recordURL, str) and len(recordURL) > 0):
							# obtain the related record's type (stored under "object" -> "type")
							recordType = get(item, "object.type")
							if(isinstance(recordType, str) and len(recordType) > 0):
								record = None
								if(recordType == "Artifact"):
									record = ArtifactRecord(URL=recordURL)
								elif(recordType == "Constituent"):
									record = ConstituentRecord(URL=recordURL)
								elif(recordType == "Exhibition"):
									record = ExhibitionRecord(URL=recordURL)
								elif(recordType == "Gallery"):
									record = GalleryRecord(URL=recordURL)
								elif(recordType == "Location"):
									record = LocationRecord(URL=recordURL)
								
								if(isinstance(record, BaseRecord)):
									# check that the record's data is available
									if(isinstance(record.data, dict)):
										# debug(record.data, format="JSON")
										
										# check that the record's UUID was found
										if(record.UUID and isinstance(record.UUID, str)):
											# map the record's data
											if(record.mapData()):
												# check that the record's entity name is available
												if(isinstance(record.entity._name, str)):
													# serialize the record's data to JSON-LD
													data = record.toJSON(compact=True)
													if(isinstance(data, str) and len(data) > 0):
														# debug(json.loads(data), format="JSON")
														# break
														
														# obtain a new cursor from the database connection
														cursor = self.database.connection.cursor()
														if(cursor):
															record_id = None
															
															if(event in ["Create", "Update", "Delete"]):
																# then determine if the record we have just encountered via the Activity Stream has already been converted...
																# here we perform the lookup via the record's entity type name and its UUID; if we find the record, we obtain its row PK (id)
																cursor.execute("SELECT id FROM records WHERE entity = %s AND uuid = %s ORDER BY id ASC", [
																	record.entity._name,
																	record.UUID
																])
																
																record_id = get(cursor.fetchone(), [0])
															
															# debug("Looked for MART.records row ID for %s (%s) and found: %s (%s)" % (record.entity._name, record.UUID, record_id, type(record_id)));
															
															if(event == "Create"):
																# if we found a valid row PK (id), we update the existing row with the newly converted record data...
																if(record_id and record_id > 0):
																	cursor.execute("UPDATE records SET datetime_updated = %s, datetime_published = %s, data = %s WHERE id = %s", [
																		get(item, "updated"),
																		get(item, "published"),
																		data,
																		record_id
																	])
																else:
																	cursor.execute("INSERT INTO records (datetime_created, datetime_updated, datetime_published, entity, uuid, data) VALUES (%s, %s, %s, %s, %s, %s)", [
																		get(item, "created"),
																		get(item, "updated"),
																		get(item, "published"),
																		record.entity._name,
																		record.UUID,
																		data
																	])
																	
																	record_id = get(cursor.fetchone(), [0])
															elif(event == "Update"):
																# if we found a valid row PK (id), we update the existing row with the newly converted record data...
																if(record_id and record_id > 0):
																	cursor.execute("UPDATE records SET datetime_updated = %s, datetime_published = %s, data = %s WHERE id = %s", [
																		get(item, "updated"),
																		get(item, "published"),
																		data,
																		record_id
																	])
																else:
																	# debug("BaseManager.processActivityStream() Unable to find the record ID for %s with UUID: %s for event: %s!" % (record.entity._name, record.UUID, event), error=True)
																	
																	cursor.execute("INSERT INTO records (datetime_created, datetime_updated, datetime_published, entity, uuid, data) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id", [
																		get(item, "created"),
																		get(item, "updated"),
																		get(item, "published"),
																		record.entity._name,
																		record.UUID,
																		data
																	])
																	
																	record_id = get(cursor.fetchone(), [0])
															elif(event == "Delete"):
																# if we found a valid row PK (id), we update the existing row with the newly converted record data...
																if(record_id and record_id > 0):
																	cursor.execute("DELETE FROM records WHERE id = %s", [
																		record_id
																	])
																else:
																	debug("BaseManager.processActivityStream() Unable to find the record ID for %s with UUID: %s for event: %s!" % (record.entity._name, record.UUID, event), error=True)
															
															# TODO Insert/Update the record's data into our Amazon Neptune graph data store...
															
															# TODO Insert ActivityStream record for this update
															cursor_as = self.database.connection.cursor()
															if(cursor_as):
																entity_id = None
																
																cursor_as.execute("SELECT id FROM entities WHERE entity = %s", [
																	record.entity._name
																])
																
																entity_id = get(cursor_as.fetchone(), [0])
																
																if(entity_id == None):
																	cursor_as.execute("INSERT INTO entities (datetime_created, entity) VALUES (current_timestamp, %s) RETURNING id", [
																		record.entity._name
																	])
																	
																	entity_id = get(cursor_as.fetchone(), [0])
																
																if(entity_id and record_id):
																	cursor_as.execute("INSERT INTO activities (datetime_created, datetime_updated, datetime_published, event, entity_id, record_id) VALUES (%s, %s, %s, %s, %s, %s)", [
																		get(item, "created"),
																		get(item, "updated"),
																		get(item, "published"),
																		event,
																		entity_id,
																		record_id
																	])
															
															if(cursor.rowcount == 1): # indicates success
																# once we have performed the UPDATE or INSERT operation, we commit the changes to the database...
																self.database.connection.commit()
																
																debug("BaseManager.processActivityStream() Successfully executed query for %s with UUID: %s!" % (record.entity._name, record.UUID))
															else:
																debug("BaseManager.processActivityStream() Failed to execute query for %s with UUID: %s!" % (record.entity._name, record.UUID), error=True)
															
															# then we close the cursor
															cursor.close()
															
															break
														else:
															debug("BaseManager.processActivityStream() Failed to obtain a database cursor!", error=True)
													else:
														debug("BaseManager.processActivityStream() Failed to serialize the record's data!", error=True)
												else:
													debug("BaseManager.processActivityStream() Failed to obtain the record's entity type!", error=True)
											else:
												debug("BaseManager.processActivityStream() Failed to map the record's data (type: %s)!" % (type(data)), error=True)
										else:
											debug("BaseManager.processActivityStream() Failed to obtain the record's UUID!", error=True)
									else:
										debug("BaseManager.processActivityStream() Failed to obtain the record's data!", error=True)
								else:
									debug("BaseManager.processActivityStream() Failed to instantiate the record for %s!" % (URL), error=True)
							else:
								debug("BaseManager.processActivityStream() Failed to obtain the record's type!", error=True)
						else:
							debug("BaseManager.processActivityStream() Failed to obtain the record's URL!", error=True)
					else:
						debug("BaseManager.processActivityStream() Failed to obtain the item change event type!", error=True)
				else:
					debug("BaseManager.processActivityStream() The item was not valid - it should be a 'dict' instance!", error=True)