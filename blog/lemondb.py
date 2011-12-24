#!/usr/bin/env python

import itertools
import logging
import time

def connect( jclassname, **args ):
	if(jclassname == "mysql"):
		mymod = __import__("mysqldb")
		return mymod._getobj(**args)
		#return mysqldb(args)
	elif(jclassname == "sqlite"):
		mymod = __import__("sqlitedb")
		return mymod._getobj(**args)

class LemonDB(object):
	def __init__(self, **kvargs):
		#print 'base class __init__'
		max_idle_time=7*3600
		self.max_idle_time = max_idle_time
		self._db_args = kvargs
		self._last_use_time = time.time()
		self._connect()

	def __del__(self):
		self.close()
		#print 'base class close'

	def close(self):
		"""Closes this database connection."""
		if getattr(self, "_conn", None) is not None:
			self._conn.close()
			self._conn = None
		#else:
			#print 'no have _conn attr'

	def reconnect(self):
		"""Closes the existing database connection and re-opens it."""
		self.close()
		self._connect()
		self._conn.autocommit(True)

	def query(self, query, *parameters):
		"""Returns a row list for the given query and parameters."""
		cursor = self._excursor()
		try:
			self._execute(cursor, query, parameters)
			column_names = [d[0] for d in cursor.description]
			return [Row(itertools.izip(column_names, row)) for row in cursor]
		finally:
			self.close()

	def get(self, query, *parameters):
		"""Returns the first row returned for the given query."""
		rows = self.query(query, *parameters)
		if not rows:
			return None
		else:
			return rows[0]
		
	def checkExist(self, query, *parameters):
		"""Returns the first row returned for the given query."""
		rows = self.query(query, *parameters)
		if not rows:
			return False
		else:
			return True
			
	def getone(self, query, *parameters):
		"""Returns the first row returned for the given query."""
		rows = self.query(query, *parameters)
		if not rows:
			return None
		else:
			if len(rows) > 1:
				raise Exception("Multiple rows returned for Database.get() query")
			else:
				return rows[0]

	def execute(self, query, *parameters):
		"""Executes the given query, returning the lastrowid from the query."""
		cursor = self._excursor()
		try:
			self._execute(cursor, query, parameters)
			return cursor.lastrowid
		finally:
			self.close()

	def executemany(self, query, parameters):
		"""Executes the given query against all tqueryhe given param sequences.

		We return the lastrowid from the query.
		"""
		cursor = self._excursor()
		try:
			cursor.executemany(query, parameters)
			return cursor.lastrowid
		finally:
			self.close()

	def _ensure_connected(self):
		# Mysql by default closes client connections that are idle for
		# 8 hours, but the client library does not report this fact until
		# you try to perform a query and it fails.  Protect against this
		# case by preemptively closing and reopening the connection
		# if it has been idle for too long (7 hours by default).
		if (self._conn is None or
			(time.time() - self._last_use_time > self.max_idle_time)):
			self.reconnect()
		self._last_use_time = time.time()

	def _excursor(self):
		self._ensure_connected()
		return self._cursor

	def _execute(self, cursor, query, parameters):
		try:
			return cursor.execute(query, parameters)
		except RuntimeError:
			logging.error("Error connecting to MySQL on %s", self.host)
			self.close()
			raise


class Row(dict):
	"""A dict that allows for object-like property access syntax."""
	def __getattr__(self, name):
		try:
			return self[name]
		except KeyError:
			raise AttributeError(name)


	

if __name__ == '__main__':
	#db = connect("sqlite", db="e:/sqlite/blog.db")
	db = connect("mysql", host="localhost", user="root", passwd="", db="news")
	db2 = connect("mysql", host="211.144.137.66", user="lemon", passwd="lemon001)(", db="wp")
	
	result = db2.get("select count(*) from wp_posts")
	print result
	#result = db.execute("insert into entries(id, title) values(%s, %s)", 5, 'test');
	#print result
