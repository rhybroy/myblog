#!/usr/bin/env python

from lemondb import LemonDB
import MySQLdb

def _getobj(**args):
	print args
	return Mysqldb(**args)

class Mysqldb(LemonDB):
	

	def _connect(self):
		self._conn = MySQLdb.connect(**self._db_args)
		self._cursor = self._conn.cursor()




