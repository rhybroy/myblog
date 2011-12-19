#!/usr/bin/env python

from lemondb import LemonDB, Row
import sqlite3


def _getobj(**args):
	print args
	return Sqlitedb(**args)

class Sqlitedb(LemonDB):
	def _connect(self):
		print 'sqlite3 _connect'
		self._database = self._db_args["db"]
		self._conn = sqlite3.connect(self._database)
		self._conn.row_factory = dict_factory
		self._cursor = self._conn.cursor()

	def _get(self, sql, *args):
		self._cursor.execute(sql)
		return self._cursor.fetchone()


def dict_factory(cursor, row):
		d = {}
		for idx, col in enumerate(cursor.description):
			d[col[0]] = row[idx]
		return Row(d)

if __name__ == '__main__':
	sqlite = Sqlitedb(db='e:/sqlite/blog.db')
	row = sqlite.getone("select * from entries")
	print row
	print row.id

