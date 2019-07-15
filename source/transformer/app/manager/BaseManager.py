from abc import ABC, abstractmethod

import json
import requests
import os
import re
import inspect
import copy
import sys

from .. utilities import get, has

# Abstract BaseManager class for all Manager entities
class BaseManager(ABC):
	
	def __init__(self):
		self.resource = None
		self.data     = None
	
	def assembleHeaders(self, headers={}):
		"""Assemble our HTTP Request Headers for the DOR API call"""
		
		apiUser    = os.getenv("MART_DOR_API_USER", None)
		apiKey     = os.getenv("MART_DOR_API_KEY", None)
		apiVersion = os.getenv("MART_DOR_API_VERSION", None)
		
		_headers = {}
		
		if(apiUser):
			if(apiKey):
				_headers["Authorization"] = "ApiKey " + apiUser + ":" + apiKey
				
				if(apiVersion):
					_headers["Accept"] = "application/json;charset=UTF-8;version=" + apiVersion
				else:
					raise RuntimeError("Missing DOR API Version Environment Variable!")
			else:
				raise RuntimeError("Missing DOR API Key Environment Variable!")
		else:
			raise RuntimeError("Missing DOR API User Environment Variable!")
		
		if(_headers):
			# Support cache toggling from the CLI
			testCaching = None
			
			if(sys.argv):
				for index, argv in enumerate(sys.argv):
					if(argv == "--cache"):
						if(sys.argv[(index + 1)]):
							testCaching = sys.argv[(index + 1)]
			
			if(testCaching == None and (os.getenv("MART_DOR_API_CACHING", "YES") == "NO")):
				_headers["X-Request-Caching"] = "NO"
			elif(testCaching == "NO"):
				_headers["X-Request-Caching"] = "NO"
			
			if(headers and len(headers) > 0):
				for index, key in enumerate(headers):
					_headers[key] = headers[key]
			
			return _headers
		
		return None
	
	def generateURI(self):
		"""Generate the URI for a DOR API resource"""
		
		return "/api/" + self.resource + "/"
	
	def generateURL(self, **kwargs):
		"""Generate the absolute URL for a DOR API resource list endpoint"""
		
		baseURL   = os.getenv("MART_DOR_BASE_URL", None)
		recordURI = self.generateURI()
		
		if(baseURL):
			if(recordURI):
				URL = baseURL + "/" + recordURI
				
				if(kwargs and len(kwargs) > 0):
					parameters = []
					
					for index, key in enumerate(kwargs):
						parameters.append(key + "=" + str(kwargs[key]))
					
					if(len(parameters) > 0):
						URL += "?" + "&".join(parameters)
				
				return URL
		
		return None
	
	def getIDs(self, offset=0, limit=100):
		headers = self.assembleHeaders(headers={
			"X-Request-Envelope": "NO", # disable the envelope
		})
		
		if(headers):
			URL = self.generateURL(offset=offset, limit=limit, fields="(id)")
			
			response = requests.get(URL, headers=headers)
			if(response):
				if(response.status_code == 200):
					data = json.loads(response.text)
					if(data):
						self.data = data
						
						return data
		
		return False