import pprint
import sched
import time
import json
import io

def sprintf(*args, end='', **kwargs):
    sio = io.StringIO()
    print(*args, **kwargs, end=end, file=sio)
    return sio.getvalue()

def debug(*args, **kwargs):
	if(args and len(args) > 0):
		if(args[0]):
			value = args[0]
			if(value):
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
				
				level = 0
				if("level" in kwargs):
					if(isinstance(kwargs["level"], int)):
						error = kwargs["level"]
					del kwargs["level"]
				
				indent = 0
				if("indent" in kwargs):
					if(isinstance(kwargs["indent"], int)):
						error = kwargs["indent"]
					del kwargs["indent"]
				
				if(label):
					print(label)
				
				if(error):
					print("\033[93;41m", end="")
				
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
	# print("repeat(delay = %s, method = %s, args = %s, kwargs = %s)" % (delay, method, args, kwargs));
	
	scheduler = kwargs.get("scheduler", None);
	
	if scheduler == None:
		scheduler = sched.scheduler(time.time, time.sleep)
	
	kwargs.pop("scheduler", None);
	
	method(*args, **kwargs)
	
	kwargs["scheduler"] = scheduler;
	
	scheduler.enter(delay, 1, repeater, (delay, method) + args, kwargs)
	scheduler.run()

def get(variable, *args, **kwargs):
	if(variable):
		value = variable
		
		if(args and len(args) > 0):
			keys = args
			
			if(len(args) == 1):
				if(isinstance(args[0], str)):
					if("." in args[0]):
						keys = args[0].split(".")
			
			for key in keys:
				if(key in value):
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
	
	return None

def has(variable, *args, **kwargs):
	value = get(variable, *args)
	if(value):
		return True
	
	return False