from abc import ABC, abstractmethod

# Abstract base class for all Model entities
class _Base(ABC):
	def __init__(self, id):
		self.type     = self.__class__.__name__
		self.id       = id
		self.resource = None
		self.data     = None
	
	def info(self):
		print("Hello, '%s' was just initialized with: id = %s; resource = %s" % (self.type, str(self.id), self.resource));
		print(self.generateURI())
	
	def generateURI(self):
		return "/api/" + self.resource + "/" + str(self.id) + "/"
	
	def getData(self):
		url = self.generateURI()
		
		print(uri)
		
		pass
	
	@abstractmethod
	def mapData(self):
		pass
	
	@abstractmethod
	def toJSON(self, data):
		pass


class Artifact(_Base):
	def __init__(self, id):
		super().__init__(id)
		self.resource = "artifact"
		self.info()
	
	def mapData(self):
		pass
	
	def toJSON(self, data):
		pass


class Constituent(_Base):
	def __init__(self, id):
		super().__init__(id)
		self.resource = "constituent"
		self.info()
	
	def mapData(self):
		pass
	
	def toJSON(self, data):
		pass


class Exhibition(_Base):
	def __init__(self, id):
		super().__init__(id)
		self.resource = "exhibition"
		self.info()
	
	def mapData(self):
		pass
	
	def toJSON(self, data):
		pass