#!/usr/bin/env python3

import sys
import datetime
import os

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
else:
	debug(level=os.getenv("MART_DEBUG_LEVEL", -1))

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