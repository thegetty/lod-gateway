import sys
import datetime

# import our utility functions (get, has, debug, repeater, etc)
from app.utilities import *

# import our source model record classes
from app.model.ArtifactRecord import *
from app.model.ConstituentRecord import *
from app.model.ExhibitionRecord import *
from app.model.LocationRecord import *

# for testing, support controlling the transformation process from the CLI
testEntity = None
testID     = None
testRecord = None

if(sys.argv):
	for index, argv in enumerate(sys.argv):
		if(argv == "--entity"):
			if(sys.argv[(index + 1)]):
				testEntity = sys.argv[(index + 1)]
		elif(argv == "--id"):
			if(sys.argv[(index + 1)]):
				testID = sys.argv[(index + 1)]

if(testEntity and testID):
	if(testEntity == "Artifact"):
		testRecord = ArtifactRecord(testID)
	elif(testEntity == "Constituent"):
		testRecord = ConstituentRecord(testID)
	elif(testEntity == "Exhibition"):
		testRecord = ExhibitionRecord(testID)
	elif(testEntity == "Location"):
		testRecord = LocationRecord(testID)
	else:
		testRecord = ArtifactRecord(826)
elif(testID):
	testRecord = ArtifactRecord(testID)
else:
	testRecord = ArtifactRecord(826)

if(testEntity):
	print("testEntity = %s; testID = %s; testRecord = %s (%s)" % (testEntity, testID, testRecord, testRecord.id))

if(testRecord):
	data = testRecord.getData()
	# print(data)
	data = testRecord.mapData()
	# print(data)
	data = testRecord.toJSON()
	print(data)

counter = 0
delay   = 2 # seconds

def checkActivityStream(stream=None):
	global counter
	
	now = datetime.datetime.now()
	counter += 1
	
	print("[%04d-%02d-%02d %02d:%02d:%02d] Checking activity stream: %s (%d)" % (now.year, now.month, now.day, now.hour, now.minute, now.second, stream, counter))
	
	# TODO call the DOR's ActivityStreams API endpoint to determine if any records have changed that need to be transformed...

# Run our checkActivityStream method every 'delay' seconds...
# repeater(delay, checkActivityStream, stream="Object")