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
		self.connects    = 0
		self.disconnects = 0
		
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
		
		self.connects += 1 # Increment the requested connections counter
		
		try:
			connection = psycopg2.connect(service)
			if(connection):
				if(isinstance(autocommit, bool)):
					connection.autocommit = autocommit
				
				self.connection = connection
				self.connections.append(connection)
				
				return connection
		except:
			debug("Database.connect() Failed to connect to the %s database!" % (self.configuration["database"]), error=True)
			return None
	
	def disconnect(self, connection=None):
		debug("Database.disconnect(connection: %s) called..." % (connection), level=1)
		
		self.disconnects += 1 # Increment the requested disconnects counter
		
		if(connection):
			if(connection in self.cursors):
				for index, cursor in enumerate(self.cursors[connection]):
					if(cursor):
						try:
							cursor.close()
						except:
							debug("Database.disconnect() Failed to close cursor (%s) for the %s database!" % (cursor, self.configuration["database"]), error=True)
					
					del self.cursors[connection][index]
				
				del self.cursors[connection]
			
			try:
				connection.close()
			except:
				debug("Database.disconnect() Failed to close connection for the %s database!" % (self.configuration["database"]), error=True)
			
			index = self.connections.index(connection)
			if(index >= 0):
				del self.connections[index]
		elif(self.connections and len(self.connections) > 0):
			for index, connection in enumerate(self.connections):
				if(connection):
					if(connection in self.cursors):
						for cindex, cursor in enumerate(self.cursors[connection]):
							if(cursor):
								try:
									cursor.close()
								except:
									debug("Database.disconnect() Failed to close cursor (%s) for the %s database!" % (cursor, self.configuration["database"]), error=True)
							
							del self.cursors[connection][cindex]
						
						del self.cursors[connection]
					
					try:
						connection.close()
					except:
						debug("Database.disconnect() Failed to close connection for the %s database!" % (self.configuration["database"]), error=True)
				
				del self.connections[index]
	
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
				debug(e)
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
					debug(e)
					
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
					debug(e)
					
					return False
			else:
				raise RuntimeError("The database connection is already closed!")
		else:
			return None
	
	def information(self):
			"""Obtain information and statistics about the current state of the database for debugging purposes."""
			
			debug("Database.information() called...", level=1)
			
			information = {
				"database": {
					"connection": {
						"host":   self.configuration["hostname"],
						"port":   self.configuration["hostport"],
						"name":   self.configuration["database"],
						"user":   self.configuration["username"],
						"shared": self.shared,
					},
					"connections": {
						"requested": self.connects,
						"known":     len(self.connections),
						"active":    0,
						"cursors":   len(self.cursors),
					},
					"disconnections": {
						"requested": self.disconnects,
					},
				},
			}
			
			connection = self.connect(autocommit=True)
			if(connection):
				cursor = self.cursor(connection=connection)
				if(cursor):
					cursor.execute("SELECT SUM(numbackends) AS connections FROM pg_stat_database")
					
					result = cursor.fetchone()
					if(result):
						if(result[0]):
							information["database"]["connections"]["active"] = result[0]
						else:
							debug("Database.information(connection: %s) The query result did not contain a 'connections' property!" % (connection), error=True)
					else:
						debug("Database.information(connection: %s) A valid query result could not be obtained!" % (connection), error=True)
				else:
					debug("Database.information(connection: %s) Unable to obtain a new database connection cursor!" % (connection), error=True)
			else:
				debug("Database.information(connection: %s) Unable to obtain a new database connection!" % (connection), error=True)
			
			self.disconnect(connection=connection)
			
			return information