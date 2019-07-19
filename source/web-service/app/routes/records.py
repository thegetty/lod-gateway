import sys
import datetime
import json
import hashlib

# import our utility functions (get, has, debug, repeater, sprintf, etc)
from .. utilities import *
from .. database import Database

from flask import Flask, Blueprint, Response

records = Blueprint("records", __name__)

@records.route("/<path:namespace>/<string:entity>/<string:UUID>")
def obtainRecord(namespace, entity, UUID):
	debug("obtainRecord(namespace: %s, entity: %s; uuid: %s) called..." % (namespace, entity, UUID))
	
	# return sprintf("You requested Namespace: %s for Entity: %s with UUID: %s" % (namespace, entity, UUID))
	
	response = None
	
	if(isinstance(entity, str) and len(entity) > 0):
		entityName  = None
		entityParts = entity.split("-")
		if(len(entityParts) > 0):
			for index, part in enumerate(entityParts):
				entityParts[index] = part.capitalize()
			entityName = "".join(entityParts)
	
	if(entityName):
		debug("Will now perform lookup for %s with UUID: %s" % (entityName, UUID))
		
		database = Database()
		if(database):
			debug("Successfully connected to the database...")
			
			if(database.connection):
				cursor = database.cursor()
				if(cursor):
					debug("Successfully obtained a database cursor...")
					
					cursor.execute("SELECT * FROM records WHERE entity = %s and uuid = %s", [
						entityName,
						UUID
					])
					
					results = cursor.fetchall()
					
					if(results and len(results) > 0):
						debug("Found %d results" % (len(results)))
						
						# debug(results, format="JSON")
						
						result = get(results, [0])
						if(result):
							debug(result)
							
							if(result.data and len(result.data) >= 0):
								# response = sprintf("Found record in the database with ID: %d of type %s" % (result.id, type(result.data)))
								
								body = json.dumps(result.data, sort_keys=False, indent=4, ensure_ascii=False)
								if(isinstance(body, str) and len(body) > 0):
									body = body.encode("utf-8")
									
									headers = {
										"Date": result.datetime_published,
										"Server": "MART/0.1",
									}
									
									hasher = hashlib.sha1()
									hasher.update(body)
									hash = hasher.hexdigest()
									
									if(hash):
										headers["E-Tag"] = hash
									
									# see https://werkzeug.palletsprojects.com/en/0.15.x/wrappers/
									response = Response(
										body,
										content_type='application/ld+json',
										status=200,
										headers=headers,
									)
								else:
									debug("The result.data could not be serialized to JSON!", error=True)
									
									response = Response("Not Found", status=404)
							else:
								debug("The result.data attribute is empty!", error=True)
								
								response = Response("Not Found", status=404)
						else:
							debug("Unable to obtain result from results!", error=True)
							
							response = Response("Not Found", status=404)
					else:
						debug("Found no results!", error=True)
						
						response = Response("Not Found", status=404)
					
					# clean up
					cursor.close()
			else:
				debug("Failed to obtain a database cursor!", error=True)
				
				response = Response("Internal Server Error", status=500)
			
			database.disconnect()
		else:
			debug("Failed to obtain a database connection!", error=True)
			
			response = Response("Internal Server Error", status=500)
	else:
		debug("No valid entity type name was specified!", error=True)
		
		response = Response("Bad Request", status=400)
	
	# clean up
	del database
	
	return response