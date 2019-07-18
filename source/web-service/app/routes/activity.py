import sys
import datetime
import json
import hashlib
import os

# import our utility functions (get, has, debug, repeater, sprintf, etc)
from .. utilities import *
from .. database import Database

from flask import Flask, Blueprint, Response

activity = Blueprint("activity", __name__)

@activity.route("/activity-stream")
@activity.route("/activity-stream/<path:path>")
def activityStream(path=None):
	debug("activityStream(path: %s) called..." % (path))
	
	response = None
	
	if(path == None):
		data = {
			"@context": "https://www.w3.org/ns/activitystreams",
			"summary": "The Getty MART Repository's Recent Activity",
			"type": "OrderedCollection",
			"id": generateURL(),
			"totalItems": 0,
			"first": {
				"id": generateURL(),
				"type": "OrderedCollection",
			},
			"last": {
				"id": generateURL(),
				"type": "OrderedCollection",
			},
			"path": path,
		}
		
		data = json.dumps(data, indent=4)
		
		response = Response(data, headers={
			"Content-Type": "application/activity+json",
		}, status=200)
	elif(isinstance(path, str) and len(path) > 0):
		position = None
		page     = None
		entity   = None
		
		paths = path.split("/")
		if(len(paths) == 1):
			pass
		
		response = Response("Internal Server Error", status=500)
	else:
		response = Response("Bad Request", status=400)
	
	return response

def generateURL():
	baseURL = os.getenv("MART_LOD_BASE_URL", None)
	
	return baseURL