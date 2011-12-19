#!/usr/bin/env python

import os.path
import re
import tornado.auth
#import tornado.database
import sqlite3
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import unicodedata

import lemondb
from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1:3306", help="blog database host")
define("mysql_database", default="blog", help="blog database name")
define("mysql_user", default="blog", help="blog database user")
define("mysql_password", default="blog", help="blog database password")


class Application(tornado.web.Application):

	def __init__(self):
		handlers = [
			(r"/", HomeHandler),
			(r"/page/(\d+)/?", HomeHandler),
			(r"/category/([^/]+)/?", CategoryHandler),
			(r"/entry/([^/]+)", EntryHandler),
			(r"/search/([^/]+)/?", SearchHandler),
			(r"/feed", FeedHandler),
			(r"/compose", ComposeHandler),
			(r"/auth/login", AuthLoginHandler),
			(r"/auth/logout", AuthLogoutHandler),
		]
		settings = dict(
			blog_title=u"Tornado Blog",
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			ui_modules={"Entry": EntryModule},
			xsrf_cookies=True,
			cookie_secret="11oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
			login_url="/auth/login",
		)
		tornado.web.Application.__init__(self, handlers, **settings)
		self.db = lemondb.connect("mysql", host="localhost", user="root", passwd="", db="blog")


class BaseHandler(tornado.web.RequestHandler):
	@property
	def db(self):
		return self.application.db

	def get_current_user(self):
		user_id = self.get_secure_cookie("user")
		if not user_id: return None
		return self.db.get("SELECT * FROM authors WHERE id = %s", int(user_id))


class HomeHandler(BaseHandler):
	def get(self, page=1):
		keyword = self.get_argument("keyword", None);
		if keyword:
			self.redirect("/search/%s"%keyword)
			return
		pagesize = 2
		page = int(page)
		if page < 1:
			page = 1
		start = (page-1)*pagesize
		entries = self.db.query("SELECT * FROM typecho_contents ORDER BY modified "
								"DESC LIMIT %s, %s", start, pagesize)
		
		self.render("index.html", entries=entries, nextpage=page+1, prepage=page-1)


class EntryHandler(BaseHandler):
	def get(self, slug):
		entry = self.db.get("SELECT * FROM typecho_contents WHERE cid = %s", False, slug)
		if not entry: 
			raise tornado.web.HTTPError(404)
		self.render("entry.html", entry=entry)


class CategoryHandler(BaseHandler):
	def get(self, mid):
		entries = self.db.query("SELECT * FROM typecho_contents a, typecho_relationships b where a.cid = b.cid and b.mid = %s ORDER BY modified DESC", mid)
		self.render("index.html", entries=entries)

class SearchHandler(BaseHandler):
	def get(self, keyword):
		entries = self.db.query("SELECT * FROM typecho_contents where title like %s ORDER BY modified DESC", "%"+keyword+"%")
		self.render("index.html", entries=entries)

class FeedHandler(BaseHandler):
	def get(self):
		entries = self.db.query("SELECT * FROM entries ORDER BY published "
								"DESC LIMIT 10")
		self.set_header("Content-Type", "application/atom+xml")
		self.render("feed.xml", entries=entries)


class ComposeHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		id = self.get_argument("id", None)
		entry = None
		if id:
			entry = self.db.get("SELECT * FROM entries WHERE id = %s", int(id))
		self.render("compose.html", entry=entry)

	@tornado.web.authenticated
	def post(self):
		id = self.get_argument("id", None)
		title = self.get_argument("title")
		text = self.get_argument("markdown")
		html = markdown.markdown(text)
		if id:
			entry = self.db.get("SELECT * FROM entries WHERE id = %s", int(id))
			if not entry: raise tornado.web.HTTPError(404)
			slug = entry.slug
			self.db.execute(
				"UPDATE entries SET title = %s, markdown = %s, html = %s "
				"WHERE id = %s", title, text, html, int(id))
		else:
			slug = unicodedata.normalize("NFKD", title).encode(
				"ascii", "ignore")
			slug = re.sub(r"[^\w]+", " ", slug)
			slug = "-".join(slug.lower().strip().split())
			if not slug: slug = "entry"
			while True:
				e = self.db.get("SELECT * FROM entries WHERE slug = %s", slug)
				if not e: break
				slug += "-2"
			self.db.execute(
				"INSERT INTO entries (author_id,title,slug,markdown,html,"
				"published) VALUES (%s,%s,%s,%s,%s,UTC_TIMESTAMP())",
				self.current_user.id, title, slug, text, html)
		self.redirect("/entry/" + slug)


class AuthLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
	@tornado.web.asynchronous
	def get(self):
		if self.get_argument("openid.mode", None):
			self.get_authenticated_user(self.async_callback(self._on_auth))
			return
		self.authenticate_redirect()
	
	def _on_auth(self, user):
		if not user:
			raise tornado.web.HTTPError(500, "Google auth failed")
		author = self.db.get("SELECT * FROM authors WHERE email = %s",
							 user["email"])
		if not author:
			# Auto-create first author
			any_author = self.db.get("SELECT * FROM authors LIMIT 1")
			if not any_author:
				author_id = self.db.execute(
					"INSERT INTO authors (email,name) VALUES (%s,%s)",
					user["email"], user["name"])
			else:
				self.redirect("/")
				return
		else:
			author_id = author["id"]
		self.set_secure_cookie("user", str(author_id))
		self.redirect(self.get_argument("next", "/"))


class AuthLogoutHandler(BaseHandler):
	def get(self):
		self.clear_cookie("user")
		self.redirect(self.get_argument("next", "/"))


class EntryModule(tornado.web.UIModule):
	def render(self, entry):
		return self.render_string("modules/entry.html", entry=entry)


def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
	main()
