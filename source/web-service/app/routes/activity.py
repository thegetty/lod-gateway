import sys
import datetime
import json
import hashlib
import os
import math

# Import the utility functions (commandOptions, get, has, put, debug, repeater, etc)
from app.utilities import *

# Import the dependency injector
from app.di import DI

# Import the data model
from app.model import *

# Import the Flask web framework
from flask import Flask, Blueprint, Response, request

# Create a new "activity" route blueprint
activity = Blueprint("activity", __name__)

@activity.route("/activity-stream")
@activity.route("/activity-stream/<path:path>")
def activityStream(path=None):
	debug("activityStream(path: %s) called..." % (path), level=1)
	
	database = DI.get("database")
	if(database):
		connection = database.connect(autocommit=True)
		if(connection):
			DI.set("connection", connection)
		else:
			return Response(status=500, headers={
				"X-Error": "Unable to obtain database connection!",
			})
	else:
		return Response(status=500, headers={
			"X-Error": "Unable to obtain database handler!",
		})
	
	response  = None
	
	positions = ["first", "last", "current", "prev", "previous", "next", "page"]
	paths     = None
	namespace = None
	entity    = None
	position  = None
	page      = None
	UUID      = None
	
	# /activity-stream
	# /activity-stream/first
	# /activity-stream/last
	# /activity-stream/page/123
	# /activity-stream/museum/collection/first
	# /activity-stream/museum/collection/last
	# /activity-stream/museum/collection/page/123
	# /activity-stream/museum/collection/object/last
	# /activity-stream/museum/collection/object/first
	# /activity-stream/museum/collection/object/page/123
	
	if(isinstance(path, str) and len(path) > 0):
		paths = path.split("/")
		if(len(paths) >= 1):
			if(paths[0] in positions):
				position = paths[0]
				
				if(position == "page"):
					if(len(paths) >= 2 and isNumeric(paths[1])):
						page = int(paths[1])
			else:
				if(isUUIDv4(paths[0])):
					UUID = paths[0]
				else:
					entity = paths[0]
					
					if(len(paths) >= 2):
						if(paths[1] in positions):
							position = paths[1]
							
							if(position == "page"):
								if(len(paths) >= 3 and isNumeric(paths[2])):
									page = int(paths[2])
	
	query = {}
	
	if(namespace):
		if(entity):
			query = {}
		else:
			query = {}
	else:
		query = {}
	
	start    = 1
	count    = Activity.count(**query)
	limit    = request.args.get("limit", default=100, type=int)
	offset   = request.args.get("offset", default=0, type=int)
	first    = 0
	last     = 0
	previous = 0
	current  = 0
	next     = 0
	pages    = 0
	data     = None
	
	if(UUID):
		activity = Activity.findFirst("uuid = :uuid:", bind={"uuid": UUID})
		if(activity):
			data = {
				"@context": "https://www.w3.org/ns/activitystreams",
				"partOf": {
					"id": generateURL(),
					"type": "OrderedCollection",
				},
			}
			
			item = generateActivityStreamItem(activity)
			if(isinstance(item, dict)):
				data.update(item)
				
				response = Response(json.dumps(data, indent=4), headers={
					"Content-Type": "application/activity+json;charset=UTF-8",
				}, status=200)
			else:
				response = Response(status=404, headers={
					"X-Error": sprintf("Activity %s was not found!" % (UUID), error=True),
				})
		else:
			response = Response(status=404, headers={
				"X-Error": sprintf("Activity %s was not found!" % (UUID)),
			})
	elif(count):
		if(count > 0):
			pages = math.ceil(count / limit)
			first = 1
			last  = pages
			
			if(position == "first"):
				previous = (first - 1)
				offset   = (first)
				next     = (first + 1)
			elif(position == "last"):
				previous = (last - 1)
				offset   = (last)
				next     = (last + 1)
			elif(position == "current"):
				response = Response(status=400, headers={
					"X-Error": "Unsupported Pagination Mnemonic (Current)",
				})
			elif(position == "page"):
				if(page):
					if(page >= 1 and page <= last):
						offset   = page
						current  = page
						previous = (offset - 1)
						next     = (offset + 1)
					else:
						response = Response(status=400, headers={
							"X-Error": "Page Offset Out Of Range",
						})
				elif(page == 0):
					offset   = 0
					current  = 0
					previous = 0
					next     = 0
				else:
					response = Response(status=400, headers={
						"X-Error": "Invalid Page Offset",
					})
			elif(isinstance(position, str)):
				response = Response(status=400, headers={
					"X-Error": sprintf("Unsupported Pagination Mnemonic (%s)" % (position)),
				})
			
			if(not response):
				if(previous < first):
					previous = 0
				
				if(next > last):
					next = 0
				
				query["offset"]   = offset
				query["limit"]    = limit
				query["ordering"] = {"id": "ASC"}
				
				data = {
					"@context": "https://www.w3.org/ns/activitystreams",
					"summary":  "The Getty MART Repository's Recent Activity",
					"type": "OrderedCollection",
					"id": generateURL(),
					"startIndex": start,
					"totalItems": count,
					"totalPages": pages,
					"maxPerPage": limit,
				}
				
				# data["meta"] = {
				# 	"path":      path,
				# 	"uuid":      UUID,
				# 	"namespace": namespace,
				# 	"entity":    entity,
				# 	"position":  position,
				# 	"count":     count,
				# 	"offset":    offset,
				# 	"limit":     limit,
				# 	"previous":  previous,
				# 	"current":   current,
				# 	"next":      next,
				# 	"first":     first,
				# 	"last":      last,
				# 	"page":      page,
				# 	"query":     query,
				# }
				#
				# debug(data, format="JSON")
				
				activities = Activity.find(**query)
				if(activities):
					debug("Found %d activities..." % (len(activities)), level=1)
					
					if(len(activities) > 0):
						if(offset == 0):
							if(first):
								data["first"] = {
									"id":   generateURL(sub=["page", str(first)]),
									"type": "OrderedCollectionPage",
								}
							
							if(last):
								data["last"] = {
									"id":   generateURL(sub=["page", str(last)]),
									"type": "OrderedCollectionPage",
								}
						else:
							data["id"] = generateURL(sub=["page", str(offset)])
							
							data["partOf"] = {
								"id":   generateURL(),
								"type": "OrderedCollection",
							}
							
							if(first):
								data["first"] = {
									"id":   generateURL(sub=["page", str(first)]),
									"type": "OrderedCollectionPage",
								}
							
							if(last):
								data["last"] = {
									"id":   generateURL(sub=["page", str(last)]),
									"type": "OrderedCollectionPage",
								}
							
							if(previous):
								data["previous"] = {
									"id":   generateURL(sub=["page", str(previous)]),
									"type": "OrderedCollectionPage",
								}
							
							if(next):
								data["next"] = {
									"id":   generateURL(sub=["page", str(next)]),
									"type": "OrderedCollectionPage",
								}
							
							items = data["orderedItems"] = []
							
							for index, activity in enumerate(activities):
								debug("%06d/%06d ~ %s ~ id = %s" % (index, count, activity, activity.id), indent=1, level=2)
								
								item = generateActivityStreamItem(activity)
								if(item):
									items.append(item)
							
							if(len(items) > 0):
								response = Response(json.dumps(data, indent=4), headers={
									"Content-Type": "application/activity+json;charset=UTF-8",
								}, status=200)
							else:
								response = Response(status=404, headers={
									"X-Error": "Activity Stream Items Not Found",
								})
					else:
						response = Response(status=404, headers={
							"X-Error": "Activity Stream Items Not Found",
						})
				else:
					response = Response(status=404, headers={
						"X-Error": "Activity Stream Items Not Found",
					})
				
				if(not response):
					response = Response(json.dumps(data, indent=4), headers={
						"Content-Type": "application/activity+json;charset=UTF-8",
					}, status=200)
		else:
			response = Response(status=404, headers={
				"X-Error": "No Activity Stream Items Found!",
			})
	else:
		response = Response(status=500, headers={
			"X-Error": "Invalid Activity Stream Record Count!",
		})
	
	if(not isinstance(response, Response)):
		response = Response(status=500, headers={
			"X-Error": "Invalid Response Data",
		})
	
	database.disconnect(connection=connection)
	
	return response

def generateActivityStreamItem(activity, **kwargs):
	debug("generateActivityStreamItem(activity: %s, kwargs: %s) called..." % (activity, kwargs), level=1)
	
	if(isinstance(activity, Activity)):
		item = {
			"id":        generateURL(sub=[activity.uuid]),
			"type":      activity.event,
			"actor":     None,
			"object":    None,
			"created":   None,
			"updated":   None,
			"published": None,
		}
		
		if(activity.datetime_created):
			item["created"] = activity.datetime_created
		
		if(activity.datetime_updated):
			item["updated"] = activity.datetime_updated
		else:
			item["updated"] = activity.datetime_created
		
		if(activity.datetime_published):
			item["published"] = activity.datetime_published
		else:
			if(activity.datetime_updated):
				item["published"] = activity.datetime_updated
			else:
				item["published"] = activity.datetime_created
		
		record = activity.record
		if(isinstance(record, Record)):
			_entity = hyphenatedStringFromCamelCasedString(record.entity)
			
			item["object"] = {
				"id":   generateURL(sub=[record.namespace, _entity, record.uuid], base=True),
				"type": record.entity,
			}
		else:
			debug("generateActivityStreamItem() Related Record for %s was invalid!" % (activity), error=True)
		
		return item
	else:
		debug("generateActivityStreamItem() Provided Activity was invalid!", error=True)
	
	return None

def generateURL(**kwargs):
	debug("generateURL(kwargs: %s) called..." % (kwargs), level=1)
	
	URL = os.getenv("MART_LOD_BASE_URL", None)
	
	if(URL):
		if(get(kwargs, "base", default=False) == False):
			URL += "/activity-stream"
		
		if("sub" in kwargs):
			if(isinstance(kwargs["sub"], list) and len(kwargs["sub"]) > 0):
				for sub in kwargs["sub"]:
					if(isinstance(sub, str) and len(sub) > 0):
						URL += "/" + sub
		
		return URL
	
	return None