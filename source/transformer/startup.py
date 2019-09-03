#!/usr/bin/env python3

import sys
import datetime

# Import the utility functions (commandOptions, get, has, put, debug, repeater, etc)
from app.utilities import *

# Configure the Transformer service
options = commandOptions({
	"debug":     False,
	"mode":      None,
	"manager":   None,
	"event":     None,
	"namespace": None,
	"entity":    None,
	"id":        None,
	"output":    None,
})

# debug(options, format="JSON")
# exit()

# Configure the debug level
if(isinstance(options["debug"], int)):
	debug(level=options["debug"]) # display debug messages with a level of or below the defined level
elif(options["debug"] == True):
	debug(level=1) # display informational messages and errors (level <= 1)
elif(options["debug"] == False):
	debug(level=-1) # only display errors (level <= -1)
else:
	debug(level=os.getenv("MART_DEBUG_LEVEL", -1))

# Import the dependency injector
from app.di import DI

# Initialise the dependency injector
di = DI()

# Import the database service handler
from app.database import Database

# Instantiate and register the database handler
database = Database(shared=True)
if(database):
	di.set("database", database)
else:
	raise RuntimeError("The database handler could not be initialized!")

# Retrieve the shared database connection, without autocommit (the default)
connection = database.connect(autocommit=False)
if(connection):
	di.set("connection", connection)
else:
	raise RuntimeError("No database connection could not be established!")

# Import the transformers
from app.transformers import *

# Import the process manager
from app.manager import *

# Import the graph store service handler
# from app.graph import GraphStore

# Instantiate and register the graph store service
# di.set("graph", GraphStore())

# Instantiate the process manager
if(options["manager"] in ["records"]):
	manager = RecordsManager()
else:
	manager = ActivityStreamManager()

if(manager):
	if(isinstance(manager, RecordsManager)): # manual/automatic records manager
		manager.process(**options)
	else: # automatic (activity streams polling) transform mode
		manager.process(**options)
		
		# count = 0
		# 
		# delay = os.getenv("MART_TRANSFORMER_STREAMS_POLL_INTERVAL", 60) # seconds
		# 
		# if(isInteger(delay)):
		# 	delay = int(delay)
		# else:
		# 	delay = 60
		# 
		# def runManagerProcess():
		# 	global count, manager, options
		# 	
		# 	now = datetime.datetime.now()
		# 	count += 1
		# 	
		# 	debug("[%04d-%02d-%02d %02d:%02d:%02d] processActivityStreams() called (%d)" % (now.year, now.month, now.day, now.hour, now.minute, now.second, count))
		# 	
		# 	manager.process(**options)
		# 
		# repeater(delay, runManagerProcess)
else:
	raise RuntimeError("Failed to initialise the process manager!")

exit()