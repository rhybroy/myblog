#!/usr/bin/env python

import os.path
import tornado.auth
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import define, options, parse_command_line

import urllib
import lemondb
import markdown2

import admin

import settings



class Application(tornado.web.Application):

	def __init__(self):
		handlers = [
			(r"/", HomeHandler),
			(r"/page/(\d+)/?", HomeHandler),
			(r"/category/([^/]+)/?", CategoryHandler),
			(r"/category/([^/]+)/(\d+)?/?", CategoryHandler),
			(r"/search/([^/]+)/?", SearchHandler),
			(r"/search/([^/]+)/(\d+)?/?", SearchHandler),
			(r"/entry/([^/]+)", EntryHandler),
			(r"/feed", FeedHandler),
			(r"/compose", admin.ComposeHandler),
			(r"/admin/list", admin.ListHandler),
			(r"/auth/login", admin.AuthLoginHandler),
			(r"/auth/logout", admin.AuthLogoutHandler),
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
		self.db = lemondb.connect("mysql", host="localhost", user="root", passwd="", db="blog", charset="utf8")


class BaseHandler(tornado.web.RequestHandler):
	@property
	def db(self):
		return self.application.db

	def get_current_user(self):
		user_id = self.get_secure_cookie("user")
		print user_id
		if not user_id: return None
		return self.db.get("SELECT * FROM typecho_users WHERE name = %s", str(user_id))
		


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
		entries = self.db.query("SELECT a.*, c.name as category, c.slug as cslug FROM typecho_contents a, typecho_relationships b, typecho_metas c where a.status = 'publish' and a.cid = b.cid and b.mid = c.mid ORDER BY a.created "
								"DESC LIMIT %s, %s", start, pagesize)
		
		categorys = self.db.query("select * from typecho_metas where type='category' order by `order`")
		recentlys = self.db.query("select title, slug, created from typecho_contents order by created desc limit 10")
		
		self.render("index.html", entries=entries, nextpage=page+1, prepage=page-1, pagetype="page", categorys=categorys, recentlys=recentlys)


class EntryHandler(BaseHandler):
	def get(self, slug):
		slug = urllib.quote(slug).lower().strip()
		entry = self.db.get("SELECT * FROM typecho_contents WHERE slug = %s and status = 'publish'", slug)
		if not entry: 
			raise tornado.web.HTTPError(404)
		
		comments = self.db.query("select * from typecho_comments where cid = %s order by created", entry.cid)
		
		categorys = self.db.query("select * from typecho_metas where type='category' order by `order`")
		recentlys = self.db.query("select title, slug, created from typecho_contents order by created desc limit 10")
		
		self.render("entry.html", entry=entry, comments=comments, categorys=categorys, recentlys=recentlys)


class CategoryHandler(BaseHandler):
	def get(self, slug, page=1):
		slug = urllib.quote(slug).lower().strip()
		mid = self.db.get("select mid from typecho_metas where slug = %s", slug).mid
		pagesize = 2
		page = int(page)
		if page < 1:
			page = 1
		start = (page-1)*pagesize
		entries = self.db.query("SELECT a.*, c.name as category, c.slug as cslug FROM typecho_contents a, typecho_relationships b, typecho_metas c where a.cid = b.cid and b.mid = c.mid and b.mid = %s and a.status = 'publish' ORDER BY created DESC LIMIT %s, %s", mid, start, pagesize)
		
		categorys = self.db.query("select * from typecho_metas where type='category' order by `order`")
		recentlys = self.db.query("select title, slug, created from typecho_contents order by created desc limit 10")
		
		self.render("index.html", entries=entries, nextpage=page+1, prepage=page-1, pagetype="category/%s"%slug, categorys=categorys, recentlys=recentlys)

class SearchHandler(BaseHandler):
	def get(self, keyword, page=1):
		pagesize = 2
		page = int(page)
		if page < 1:
			page = 1
		start = (page-1)*pagesize
		entries = self.db.query("SELECT a.*, c.name as category, c.slug as cslug FROM typecho_contents a, typecho_relationships b, typecho_metas c where a.cid = b.cid and b.mid = c.mid and a.title like %s ORDER BY a.created DESC LIMIT %s, %s", "%"+keyword+"%", start, pagesize)
		
		categorys = self.db.query("select * from typecho_metas where type='category' order by `order`")
		recentlys = self.db.query("select title, slug, created from typecho_contents order by created desc limit 10")
		
		self.render("index.html", entries=entries, nextpage=page+1, prepage=page-1, pagetype="search/%s"%keyword, categorys=categorys, recentlys=recentlys)

class FeedHandler(BaseHandler):
	def get(self):
		entries = self.db.query("SELECT * FROM entries ORDER BY published "
								"DESC LIMIT 10")
		self.set_header("Content-Type", "application/atom+xml")
		self.render("feed.xml", entries=entries)



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
