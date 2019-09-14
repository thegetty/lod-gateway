import pprint
import sched
import time
import json
import io
import os
import sys
import re

def isNumeric(value):
	return re.match(r"^([0-9\-\+\.]+)$", str(value))

def isInteger(value):
	return re.match(r"^([0-9\-\+]+)$", str(value))

def isFloat(value):
	return re.match(r"^([0-9\-\+]+\.[0-9]+)$", str(value))

def isCallable(klass=None, method=None):
	debug("isCallable(method: %s, klass: %s) called..." % (method, klass), level=1)
	
	if(isinstance(klass, object) and isinstance(method, str)):
		return callable(getattr(klass, method, None))
	else:
		return callable(method)
	
	return False

def isURL(value):
	if(isinstance(value, str) and len(value) > 0 and re.match(r"^http(s)://(.*)", value)):
		return True
	
	return False

def isUUIDv4(value): # c3fedd32-16f2-4141-a3ea-94e6a76713ef 8-4-4-4-12
	if(isinstance(value, str) and len(value) > 0 and re.match(r"^[0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12}$", value)):
		return True
	
	return False

def sprintf(*args, end='', **kwargs):
	sio = io.StringIO()
	print(*args, **kwargs, end=end, file=sio)
	return sio.getvalue()

def debug(*args, **kwargs):
	glo = globals()
	
	# when no args have been defined
	if(not (args and len(args) > 0)):
		# but kwargs have, configure and return
		if(kwargs and len(kwargs) > 0):
			if("level" in kwargs):
				if(isinstance(kwargs["level"], int)):
					put(glo, "_mart_.debug.level", kwargs["level"])
			
			if("output" in kwargs):
				if(kwargs["output"]):
					put(glo, "_mart_.debug.output", kwargs["output"])
			
			return
	
	if(args and len(args) > 0):
		value = args[0]
		
		format = None
		if("format" in kwargs):
			if(isinstance(kwargs["format"], str) and len(kwargs["format"]) > 0):
				format = kwargs["format"]
			del kwargs["format"]
		
		label = None
		if("label" in kwargs):
			if(isinstance(kwargs["label"], str) and len(kwargs["label"]) > 0):
				label = kwargs["label"]
			del kwargs["label"]
		
		error = False
		if("error" in kwargs):
			if(isinstance(kwargs["error"], bool)):
				error = kwargs["error"]
			del kwargs["error"]
		
		dump = False
		if("dump" in kwargs):
			if(isinstance(kwargs["dump"], bool)):
				dump = kwargs["dump"]
			del kwargs["dump"]
		
		level = 0
		if("level" in kwargs):
			if(isinstance(kwargs["level"], int)):
				level = kwargs["level"]
			del kwargs["level"]
		
		indent = 0
		if("indent" in kwargs):
			if(isinstance(kwargs["indent"], int)):
				indent = kwargs["indent"]
			del kwargs["indent"]
		
		if(error):
			if(level == 0):
				level = -1
		
		# should we display the debug message based on the level?
		_level = get(glo, "_mart_.debug.level", default=0)
		if(isinstance(_level, int)):
			if(isinstance(level, int)):
				if(level > _level):
					return
		
		# where should we output the logs?
		_output = get(glo, "_mart_.debug.output")
		
		if(label):
			print(label)
		
		if(indent > 0):
			print("".join((" " * indent)), end="")
		
		if(error):
			print("\033[93;41m", end="")
		
		if(dump):
			values = {}
			
			for key in dir(value):
				if(isinstance(key, str)):
					if(not key.startswith("_")):
						val = getattr(value, key)
						if(not callable(val)):
							values[key] = val
			
			value = values
		
		if(isinstance(value, str)):
			placeholders = [value]
			for index, arg in enumerate(args):
				if(index > 0):
					placeholders.append(arg)
			
			print(sprintf(*placeholders))
		else:
			if(format == "JSON"):
				print(json.dumps(value, sort_keys=True, indent=4))
			else:
				pp = pprint.PrettyPrinter(**kwargs)
				pp.pprint(value)
		
		if(error):
			print("\033[0m", end="")
	else:
		print()

def repeater(delay, method, *args, **kwargs):
	debug("repeat(delay = %s, method = %s, args = %s, kwargs = %s)" % (delay, method, args, kwargs));
	
	scheduler = kwargs.get("scheduler", None);
	
	if(scheduler == None):
		scheduler = sched.scheduler(time.time, time.sleep)
	
	kwargs.pop("scheduler", None);
	
	method(*args, **kwargs)
	
	kwargs["scheduler"] = scheduler;
	
	scheduler.enter(delay, 1, repeater, (delay, method) + args, kwargs)
	scheduler.run()

def get(variable, *args, **kwargs):
	value = None
	
	if(variable):
		value = variable
		
		if(args and len(args) > 0):
			keys = args
			
			if(len(keys) == 1):
				if(isinstance(keys[0], str) and len(keys[0]) > 0):
					if("." in keys[0]):
						keys = keys[0].split(".")
					else:
						keys = [keys[0]]
				elif(isinstance(keys[0], list)):
					keys = keys[0]
				else:
					keys = []
			
			for index, key in enumerate(keys):
				# debug("key[%d] = %s (%s) => %s (%s)" % (index, key, type(key), value, type(value)))
				
				if(isinstance(value, list) and isinstance(key, int) and (key < len(value))):
					value = value[key]
				elif(isinstance(value, tuple) and isinstance(key, int) and (key < len(value))):
					value = value[key]
				elif(isinstance(key, str) and (isinstance(value, dict)) and (key in value)):
					value = value[key]
				else:
					value = None
					break
				
				if(value == None):
					break
	
	if(value == None):
		if("default" in kwargs):
			return kwargs["default"]
	
	return value

def has(variable, *args, **kwargs):
	value = get(variable, *args)
	if(value):
		return True
	
	return False

def put(variable, keys, item):
	if("." in keys):
		key, rest = keys.split(".", 1)
		
		if(key not in variable):
			variable[key] = {}
		
		put(variable[key], rest, item)
	else:
		variable[keys] = item

def date(format=None, timestamp=None, **kwargs):
	# debug("date(format: %s) called..." % (format))
	
	from datetime import datetime
	import pytz
	
	if(format == None):
		format = "%Y-%m-%d %H:%M:%S"
	
	# debug("date() format = %s" % (format))
	
	if(timestamp):
		now = timestamp
	else:
		timezone = os.getenv("TZ", "America/Los_Angeles")
		tzinfo   = pytz.timezone(timezone)
		if(tzinfo):
			now = datetime.now(tzinfo)
		else:
			now = datetime.now()
	
	if(now):
		# debug("timezone = %s (%s)" % (now.strftime("%Z"), now.strftime("%z")))
		return now.strftime(format)
	
	return None

def commandOptions(options):
	"""Supports parsing a dictionary of default options and replacing any defined via the command line and returning the merged set"""
	
	if(isinstance(options, dict) and len(options) > 0):
		if(sys.argv and len(sys.argv) > 0):
			# debug(options, format="JSON")
			
			for option in options:
				count = 0
				position = 0
				
				# debug("option: %s" % (option), indent=1)
				
				for index, argv in enumerate(sys.argv):
					# debug("position: %02d; index: %02d; argv: %s" % (position, index, argv), indent=2)
					
					if(index > 0):
						value = None
						
						if(argv.startswith("--")):
							if(argv.find(option) >= 0):
								position = index
								
								arg = argv.replace(option, "").strip("-")
								if(isinstance(arg, str) and len(arg) > 0):
									if(arg in ["with", "enabled"]):
										value = True
									elif(arg in ["without", "disabled"]):
										value = False
								else:
									if(isinstance(options[option], bool)):
										value = (not options[option])
								
								if(isinstance(value, bool)):
									options[option] = value
							elif(position > 0):
								break
						else:
							if(position > 0 and index >= position):
								# if((index + 1) < len(sys.argv) and isinstance(sys.argv[(index + 1)], str) and not sys.argv[(index + 1)].startswith("--")):
								if(isNumeric(argv)):
									if(isFloat(argv)):
										value = float(argv)
									else:
										value = int(argv)
								else:
									value = argv
								
								if(count >= 1):
									if(isinstance(options[option], list)):
										options[option].append(value)
									else:
										options[option] = [options[option], value]
								else:
									options[option] = value
								
								count += 1
						
						# debug("value: %s (%s)" % (value, options[option]), indent=3)
						
					# debug("option: %s; count: %02d; index: %02d; argv: %s; value: %s" % (option, count, index, argv, options[option]), indent=1)
				
				# debug()
	
	return options

def camelCasedStringFromHyphenatedString(string):
	if(isinstance(string, str) and len(string) > 0):
		parts = string.split("-")
		if(len(parts) > 0):
			for index, part in enumerate(parts):
				parts[index] = part.lower().capitalize()
			
			string = "".join(parts)
	
	return string

def hyphenatedStringFromCamelCasedString(string):
	if(isinstance(string, str) and len(string) > 0):
		# Split the string on uppercase characters
		parts = re.findall("[A-Z][^A-Z]*", string)
		if(parts and len(parts) > 0):
			# Lowercase each part of the string
			for index, part in enumerate(parts):
				parts[index] = part.lower()
			
			# Hyphenate the parts
			string = "-".join(parts)
	
	return string

def hyphenatedStringFromSpacedString(string):
	if(isinstance(string, str) and len(string) > 0):
		# Split the string on spaces
		parts = string.split(" ")
		if(parts and len(parts) > 0):
			# Lowercase each part of the string
			for index, part in enumerate(parts):
				parts[index] = part.lower()
			
			# Hyphenate the parts
			string = "-".join(parts)
	
	return string
