import sys
import datetime

# import our utility functions (get, has, debug, repeater, etc)
from app.utilities import *

# import our source model record classes
from app.transformers.museum.collection.record.ArtifactRecord import *
from app.transformers.museum.collection.record.ConstituentRecord import *
from app.transformers.museum.collection.record.ExhibitionRecord import *
from app.transformers.museum.collection.record.LocationRecord import *

from app.manager.ArtifactManager import *

# for testing, support controlling the transformation process from the CLI
testEntity    = None
testID        = None
testMode      = None
testDirection = None

if(sys.argv):
	for index, argv in enumerate(sys.argv):
		if(argv == "--entity"):
			if(sys.argv[(index + 1)]):
				testEntity = sys.argv[(index + 1)]
		elif(argv == "--id"):
			if(sys.argv[(index + 1)]):
				testID = sys.argv[(index + 1)]
		elif(argv == "--mode"):
			if(sys.argv[(index + 1)]):
				testMode = sys.argv[(index + 1)]
		elif(argv == "--position"):
			if(sys.argv[(index + 1)] and sys.argv[(index + 1)] in ["first", "last", "current"]):
				testDirection = sys.argv[(index + 1)]

if(testMode == "manager"):
	if(testDirection):
		direction = testDirection
	else:
		direction = "last"
	
	manager = BaseManager()
	if(manager):
		manager.processActivityStream(direction=direction)
else:
	testRecord = None
	if(testEntity and testID):
		if(testEntity == "Artifact"):
			testRecord = ArtifactRecord(id=testID)
		elif(testEntity == "Constituent"):
			testRecord = ConstituentRecord(id=testID)
		elif(testEntity == "Exhibition"):
			testRecord = ExhibitionRecord(id=testID)
		elif(testEntity == "Location"):
			testRecord = LocationRecord(id=testID)
		else:
			testRecord = ArtifactRecord(id=826)
	elif(testID):
		testRecord = ArtifactRecord(id=testID)
	else:
		testRecord = ArtifactRecord(id=826)
	
	if(testEntity):
		debug("testEntity = %s; testID = %s; testRecord = %s (%s)" % (testEntity, testID, testRecord, testRecord.id))
	
	if(testRecord):
		data = testRecord.getData()
		# debug(data)
		data = testRecord.mapData()
		# debug(data)
		data = testRecord.toJSON()
		debug(data)

counter = 0
delay   = 2 # seconds

def checkActivityStream(stream=None):
	global counter
	
	now = datetime.datetime.now()
	counter += 1
	
	debug("[%04d-%02d-%02d %02d:%02d:%02d] Checking activity stream: %s (%d)" % (now.year, now.month, now.day, now.hour, now.minute, now.second, stream, counter))
	
	# TODO call the DOR's ActivityStreams API endpoint to determine if any records have changed that need to be transformed...

# Run our checkActivityStream method every 'delay' seconds...
# repeater(delay, checkActivityStream, stream="Object")