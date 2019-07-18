import psycopg2

from psycopg2.extras import RealDictCursor, NamedTupleCursor

import os

from .. utilities import has, get, sprintf, debug

class Database:
	def __init__(self):
		debug("Database.__init__() called...")
		
		self.connection = None
		self.cursors    = []
		
		self.configuration = {
			"hostname": os.getenv("MART_POSTGRES_HOST", None),
			"hostport": os.getenv("MART_POSTGRES_PORT", None),
			"database": os.getenv("MART_POSTGRES_DB", None),
			"username": os.getenv("MART_POSTGRES_USER", None),
			"password": os.getenv("MART_POSTGRES_PASSWORD", None),
		}
		
		debug("Database.__init__() configuration = %o", self.configuration)
		
		self.connection = self.connect()
	
	def connect(self):
		debug("Database.connect() called...")
		
		self.configuration["hostname"] = "postgres"
		self.configuration["hostport"] = "5432"
		
		service = sprintf("host=%s port=%s dbname=%s user=%s password=%s" % (
			self.configuration["hostname"],
			self.configuration["hostport"],
			self.configuration["database"],
			self.configuration["username"],
			self.configuration["password"]
		))
		
		debug("Database.connect() service = %s" % (service))
		
		try:
			self.connection = psycopg2.connect(service)
			if(self.connection):
				return self.connection
		except:
			debug("Database.connect() Failed to connect to the %s database!" % (self.configuration["database"]), error=True)
			return None
	
	def disconnect(self):
		debug("Database.disconnect() called...")
		
		if(self.cursors and len(self.cursors) > 0):
			for cursor in self.cursors:
				if(cursor):
					try:
						cursor.close()
					except:
						debug("Database.disconnect() Failed to close cursor (%s) for the %s database!" % (cursor, self.configuration["database"]), error=True)
		
		if(self.connection):
			try:
				self.connection.close()
			except:
				debug("Database.disconnect() Failed to close connection for the %s database!" % (self.configuration["database"]), error=True)
	
	def cursor(self, factory=NamedTupleCursor):
		debug("Database.cursor(factory: %s) called..." % (type(factory)))
		
		if(self.connection):
			try:
				cursor = self.connection.cursor(cursor_factory=factory)
				if(cursor):
					debug("Database.cursor() Created cursor of type: %s" % (type(cursor)))
					
					self.cursors.append(cursor)
					
					return cursor
			except:
				debug("Database.cursor() Failed to create a new cursor for the %s database!" % (self.configuration["database"]), error=True)
				return None
		else:
			debug("Database.cursor() Unable to create a new cusor as there is no valid connection to the %s database!" % (self.configuration["database"]), error=True)
			return None