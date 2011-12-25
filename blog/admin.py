#!/usr/bin/env python
#coding:utf-8

import tornado.web
import tornado.auth

import markdown2
import urllib
import re
import hashlib

from blog import BaseHandler		

class ListHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		page = self.get_argument("page", 1);
		pagesize = 20
		page = int(page)
		if page < 1:
			page = 1
		start = (page-1)*pagesize
		entries = self.db.query("SELECT cid, title, slug, status FROM typecho_contents ORDER BY created "
								"DESC LIMIT %s, %s", start, pagesize)
		
		total = self.db.getint("select count(*) from typecho_contents")
		hasNextPage = total > page*pagesize
		
		self.render("admin/index.html", entries=entries, nextpage=page+1, prepage=page-1, hasNextPage=hasNextPage)
		
class ComposeHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		id = self.get_argument("id", None)
		entry = None
		if id:
			entry = self.db.get("SELECT * FROM typecho_contents WHERE cid = %s", int(id))
			entry.mid = self.db.get("SELECT mid FROM typecho_relationships WHERE cid = %s", int(id))
			if entry.mid:
				entry.mid = entry.mid.mid
		categorys = self.db.query("select * from typecho_metas where type='category' order by `order`")
		
		self.render("editor.html", entry=entry, categorys=categorys)
	
	@tornado.web.authenticated
	def post(self):
		id = self.get_argument("id", None)
		mid = self.get_argument("mid")
		title = self.get_argument("title")
		text = self.get_argument("markdown")
		html = markdown2.markdown(text)
		if id:
			entryBL = self.db.checkExist("SELECT cid FROM typecho_contents WHERE cid = %s", int(id))
			if not entryBL: 
				raise tornado.web.HTTPError(404)
			title = title.encode("utf-8")
			slug = re.sub(r"\s+", "-", title)
			slug = urllib.quote_plus(slug).lower().strip()
			self.db.execute(
				"UPDATE typecho_contents SET title = %s, slug = %s, markdown = %s, html = %s, modified=now() "
				"WHERE cid = %s", title, slug, text, html, int(id))
			self.db.execute(
				"update typecho_relationships set mid = %s where cid = %s", int(mid), int(id))
		else:
			slug = urllib.quote_plus(title.encode("utf-8")).lower().strip()
			
			if not slug: 
				slug = "entry"
			while True:
				e = self.db.get("SELECT * FROM typecho_contents WHERE slug = %s", slug)
				if not e: 
					break
				slug += "-2"
			self.db.execute(
				"INSERT INTO typecho_contents (authorId,title,slug,markdown,html,"
				"created) VALUES (%s,%s,%s,%s,%s,now())",
				1, title, slug, text, html)
			self.db.execute(
				"insert typecho_relationships(cid, mid) values(%s, %s)", int(id), int(mid))
			postInMetaTotal = self.db.get("select count(*) from typecho_relationships where mid = %s", int(mid))
			
		self.redirect("/entry/" + slug)


class AuthLoginHandler(BaseHandler):
	def get(self):
		self.render("admin/login.html", tipmessages=None)
		
	def post(self):
		username = self.get_argument("username")
		password = self.get_argument("password")
		rememberme = self.get_argument("rememberme", None)
		tipmessages = []
		if(len(username) <= 0 or len(password) <= 0):
			tipmessages.append("请输入用户名和密码!")
		else:	
			author = self.db.get("SELECT * FROM typecho_users WHERE name = %s",
								 username)
			if not author:
				tipmessages.append("用户不存在!")
			elif hashlib.md5(password+author.authcode).hexdigest() != author.password:
					tipmessages.append("密码错误!")
			else:
				self.set_secure_cookie("user", str(author.name))
		if len(tipmessages) > 0:
			self.render("admin/login.html", tipmessages=tipmessages)
		else:
			print '登录成功'
			self.redirect(self.get_argument("redirect_to", "/admin/list"))

class AuthLogoutHandler(BaseHandler):
	def get(self):
		self.clear_cookie("user")
		self.redirect(self.get_argument("next", "/"))


