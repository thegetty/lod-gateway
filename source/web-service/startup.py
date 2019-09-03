#!/usr/bin/env python3

import sys
import datetime
import os
import psutil

# os.environ["MART_LOD_BASE_URL"] = "http://localhost:5100"

# Import the utility functions (commandOptions, get, has, put, debug, repeater, etc)
from app.utilities import *

# Configure the Transformer service
options = commandOptions({
	"debug": False,
})

# Configure the debug level
if(isinstance(options["debug"], int)):
	debug(level=options["debug"]) # display debug messages with a level of or below the defined level
elif(options["debug"] == True):
	debug(level=1) # display informational messages and errors (level <= 1)
elif(options["debug"] == False):
	debug(level=-1) # only display errors (level <= -1)

# debug(level=3)

# Import the dependency injector
from app.di import DI

# Import the database service handler
from app.database import Database

# Import the graph store service handler
# from app.graph import GraphStore

# Initialise the dependency injector
di = DI()

# Instantiate and register the database service
di.set("database", Database(shared=False))

# Instantiate and register the graph store service
# di.set("graph", GraphStore(shared=False))

# Import the Flask web framework
from flask import Flask, Response

# Import our Flask route handlers
from app.routes.activity import activity
from app.routes.records import records

# Initialise our Flask application
app = Flask(__name__)

# Register our Flask route handler "blueprints"
app.register_blueprint(activity)
app.register_blueprint(records)

# Establish any default routes
@app.route("/")
def welcome():
	now = datetime.datetime.now()
	
	body = sprintf("Welcome to the Museum Linked Art Data Service at %02d:%02d:%02d on %02d/%02d/%04d" % (now.hour, now.minute, now.second, now.month, now.day, now.year))
	
	return Response(body, status=200)

@app.before_request
def beforeRequest():
	debug("%s - beforeRequest() called..." % (__file__), level=1)

@app.after_request
def afterRequest(response):
	"""The after_request decorator allows us to augment responses after the request has completed, but before the response is returned to the client."""
	
	debug("%s - afterRequest() called... response.headers = %s" % (__file__, type(response.headers)), level=1)
	
	database = DI.get("database")
	if(not database):
		debug("No database connection could be established!", error=True)
		return response
	
	information = database.information()
	if(not isinstance(information, dict)):
		debug("No database information could be obtained!", error=True)
		return response
	
	process = psutil.Process()
	if(not process):
		debug("No process information instance could be obtained!", error=True)
		return response
	
	information["process"] = {
		"id": os.getpid(),
		"memory": {
			"info": process.memory_full_info(),
			"used": process.memory_full_info().uss,
		}
	}
	
	debug(information, format="JSON", label="Process Information", level=2)
	
	if(os.getenv("MART_WEB_DEBUG_HEADER", "NO") == "YES"):
		# Obtain the headers
		headers = response.headers
		if(not headers):
			debug("No response headers could be obtained!", error=True)
			return response
		
		headers["X-Process-Information"] = json.dumps(information)
		
		# Adjust the headers
		response.headers = headers
	
	return response

@app.teardown_request
def teardownRequest(response):
	debug("%s - teardownRequest() called..." % (__file__), level=1)