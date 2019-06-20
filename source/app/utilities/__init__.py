import sched, time

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
