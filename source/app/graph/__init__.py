import os

from app.utilities import has, get, sprintf, debug

class GraphStore():
	
	def __init__(self):
		debug("GraphStore.__init__() called...", level=1)
		
		self.connection = None
		
		self.configuration = {
			"hostname":  os.getenv("MART_NEPTUNE_HOST", None),
			"hostport":  os.getenv("MART_NEPTUNE_PORT", None),
			"graphname": os.getenv("MART_NEPTUNE_GRAPH", None),
			"username":  os.getenv("MART_NEPTUNE_USERNAME", None),
			"password":  os.getenv("MART_NEPTUNE_PASSWORD", None),
		}
		
		debug("GraphStore.__init__() configuration = %o", self.configuration, level=2)
		
		self.connection = self.connect()
	
	def connect(self):
		pass
	
	def disconnect(self):
		pass