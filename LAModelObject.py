from LAModelComponent import LAComponentType, LABaseComponent
from DOR_data_access import DORDataAccessObject
import json


class LAModelObject(LABaseComponent):
	def __init__(self):
		super().__init__()
		self.component_type = LAComponentType.Object
		self.dor_data_access = DORDataAccessObject()
		
	def get_id_list(self):
		return [826, 827]

	def get_data(self, id):
		data = self.dor_data_access.get_data(id)
		return data

	def to_jsonld(self, data):
		pass











