import os
import traceback

# Import the psycopg2 PostgreSQL client module
import psycopg2
from psycopg2.extras import RealDictCursor, NamedTupleCursor

# Import the utility functions (commandOptions, get, has, put, debug, repeater, etc)
from app.utilities import has, get, sprintf, debug

class Database:
	
	def __init__(self, shared=True):
		debug("Database.__init__(shared: %s) called..." % (shared), level=1)
		
		self.configuration = {
			"hostname": os.getenv("MART_POSTGRES_HOST", None),
			"hostport": os.getenv("MART_POSTGRES_PORT", None),
			"database": os.getenv("MART_POSTGRES_DB", None),
			"username": os.getenv("MART_POSTGRES_USER", None),
			"password": os.getenv("MART_POSTGRES_PASSWORD", None),
		}
		
		debug("Database.__init__(shared: %s) configuration = %s" % (shared, self.configuration), level=2)
		
		self.connection  = None
		self.connections = []
		self.cursors     = {}
		
		# how should connections be managed? as a list or as a singular connection or should this be handled outside of the class?
		# should the DI be able to handle it by providing a wrapper method that is called when the DI is 'got' that then creates a new DB instance,
		# instead of just returning a single shared DB instance?
		# the issue is with the web service which could need a DB connection per request - it may just be better to handle the creation of the DB instance/connection
		# in the request handler on a per-handler basis, rather than over complicating this class?
		self.shared = shared
		
		if(self.shared == True):
			connection = self.connect()
			if(connection and connection.closed == 0):
				self.connection = connection
				self.connections.append(connection)
	
	def __del__(self):
		# debug("Database.__del__() called...", level=1)
		# if(self.connection):
		# 	if(self.connection.closed == 0):
		#		self.disconnect()
		pass
	
	def connect(self, autocommit=False):
		debug("Database.connect(autocommit: %s) called..." % (autocommit), level=1)
		
		if(self.shared):
			if(self.connection and self.connection.closed == 0):
				if(isinstance(autocommit, bool)):
					self.connection.autocommit = autocommit
				
				return self.connection
		
		service = sprintf("host=%s port=%s dbname=%s user=%s password=%s" % (
			self.configuration["hostname"],
			self.configuration["hostport"],
			self.configuration["database"],
			self.configuration["username"],
			self.configuration["password"]
		))
		
		debug("Database.connect(autocommit: %s) service = %s" % (autocommit, service), level=2)
		
		try:
			connection = psycopg2.connect(service)
			if(connection):
				if(isinstance(autocommit, bool)):
					connection.autocommit = autocommit
				
				self.connection = connection
				self.connections.append(connection)
				
				return connection
		except Exception as e:
			debug("Database.connect() Failed to connect to the %s database!" % (self.configuration["database"]), error=True)
			debug(e, error=True, indent=1)
		
		return None
	
	def disconnect(self, connection=None):
		debug("Database.disconnect(connection: %s) called..." % (connection), level=1)
		
		if(connection):
			if(connection in self.cursors):
				for cursor in self.cursors[connection]:
					if(cursor):
						try:
							cursor.close()
						except Exception as e:
							debug("Database.disconnect() Failed to close cursor (%s) for the %s database!" % (cursor, self.configuration["database"]), error=True)
							debug(e, error=True, indent=1)
			
			try:
				connection.close()
			except Exception as e:
				debug("Database.disconnect() Failed to close connection for the %s database!" % (self.configuration["database"]), error=True)
				debug(e, error=True, indent=1)
		elif(self.connections and len(self.connections) > 0):
			for connection in self.connections:
				if(connection):
					if(connection in self.cursors):
						for cursor in self.cursors[connection]:
							if(cursor):
								try:
									cursor.close()
								except Exception as e:
									debug("Database.disconnect() Failed to close cursor (%s) for the %s database!" % (cursor, self.configuration["database"]), error=True)
									debug(e, error=True, indent=1)
					
					try:
						connection.close()
					except Exception as e:
						debug("Database.disconnect() Failed to close connection for the %s database!" % (self.configuration["database"]), error=True)
						debug(e, error=True, indent=1)
	def cursor(self, connection=None, factory=NamedTupleCursor):
		debug("Database.cursor(connection: %s, factory: %s) called..." % (connection, factory), level=1)
		
		if(not connection):
			connection = self.connection
		
		if(connection):
			try:
				cursor = connection.cursor(cursor_factory=factory)
				if(cursor):
					debug("Database.cursor() Created cursor of type: %s" % (type(cursor)), level=2)
					
					if(connection in self.cursors):
						self.cursors[connection].append(cursor)
					else:
						self.cursors[connection] = [cursor]
					
					return cursor
				else:
					debug("Database.cursor() Failed to create a new cursor for the %s database!" % (self.configuration["database"]), error=True)
					return None
			except Exception as e:
				debug("Database.cursor() Failed to create a new cursor for the %s database!" % (self.configuration["database"]), error=True)
				debug(e, error=True, indent=1)
				
				traceback.print_exc()
				
				return None
		else:
			debug("Database.cursor() Unable to create a new cusor as there is no valid connection to the %s database!" % (self.configuration["database"]), error=True)
			return None
	
	def commit(self, connection=None):
		debug("Database.commit(connection: %s) called..." % (connection), level=1)
		
		if(not connection):
			connection = self.connection
		
		if(connection):
			if(connection.closed == 0):
				try:
					connection.commit()
					
					return True
				except Exception as e:
					debug("Database.commit() Failed!", error=True)
					debug(e, error=True, indent=1)
					
					return False
			else:
				raise RuntimeError("The database connection is already closed!")
		else:
			return None
	
	def rollback(self, connection=None):
		debug("Database.rollback(connection: %s) called..." % (connection), level=1)
		
		if(not connection):
			connection = self.connection
		
		if(connection):
			if(connection.closed == 0):
				try:
					connection.rollback()
					
					return True
				except Exception as e:
					debug("Database.rollback() Failed!", error=True)
					debug(e, error=True, indent=1)
					
					return False
			else:
				raise RuntimeError("The database connection is already closed!")
		else:
			return None