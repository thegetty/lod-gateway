from . BaseManager import BaseManager

from .. utilities import get, has

# Abstract BaseManager class for all Manager entities
class ArtifactManager(BaseManager):
	
	def __init__(self):
		self.resource = "artifact"