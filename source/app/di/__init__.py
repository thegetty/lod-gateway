from app.utilities import has, get, sprintf, debug

class DI(object):
	"""Dependency Injector"""
	
	services = None
	
	def __init__(self):
		self.services = {}
		
		# override the instance get method
		self.get = self._get
		self.set = self._set
		self.has = self._has
		
		globals()["di"] = self
	
	@classmethod
	def set(cls, name, service):
		"""Register a service with the DI via a class method call"""
		
		glo = globals()
		if(glo):
			if("di" in glo):
				di = glo["di"]
				if(isinstance(di, DI)):
					return di.set(name, service)
		
		return False
	
	def _set(self, name, service):
		"""Register a service with the DI via an instance method call"""
		
		if(isinstance(name, str)):
			self.services[name] = service
			
			return True
		
		return False
	
	@classmethod
	def get(cls, *args):
		"""Obtain a registered service from the DI via a class method call"""
		
		glo = globals()
		if(glo):
			if("di" in glo):
				di = glo["di"]
				if(isinstance(di, DI)):
					if(args and args[0]):
						name = args[0]
						if(isinstance(name, str) and len(name) > 0):
							return di.get(name)
					
					return di
		
		return None
	
	def _get(self, name):
		"""Obtain a registered service from the DI via an instance method call"""
		
		if(isinstance(name, str) and len(name) > 0):
			if(name in self.services):
				return self.services[name]
		
		return None
	
	@classmethod
	def has(cls, name):
		"""Check if a service has been registered with the DI via a class method call"""
		
		glo = globals()
		if(glo):
			if("di" in glo):
				di = glo["di"]
				if(isinstance(di, DI)):
					return di.has(name, service)
		
		return False
	
	def _has(self, name):
		"""Check if a service has been registered with the DI via an instance method call"""
		
		if(isinstance(name, str) and len(name) > 0):
			if(name in self.services):
				return True
		
		return False
