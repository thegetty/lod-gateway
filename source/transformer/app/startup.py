import utilities # imported from /app/utilities
import datetime

counter = 0;

def check_activity_stream(stream=None):
	global counter
	
	now = datetime.datetime.now()
	
	counter += 1
	
	print("[%04d-%02d-%02d %02d:%02d:%02d] Checking activity stream: %s (%d)" % (now.year, now.month, now.day, now.hour, now.minute, now.second, stream, counter))

# now run our check_activity_stream method every x seconds...
utilities.repeater(2, check_activity_stream, stream="Object")