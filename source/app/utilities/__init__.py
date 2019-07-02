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
				if("format" in kwargs):
					format = kwargs["format"]
					del kwargs["format"]
				
				if(format == "JSON"):
					print()
					print(json.dumps(value, sort_keys=True, indent=4))
					print()
				else:
					print()
					pp = pprint.PrettyPrinter(**kwargs)
					pp.pprint(value)
					print()
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