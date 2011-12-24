import requests
import re
import lemondb

if __name__ == "__main__":
    db = lemondb.connect("mysql", host="localhost", user="root", passwd="", db="blog", charset="utf8")
    next = 'http://oo.xx/?paged=1'
    if next != None:
        r = requests.get(next)
        html = r.content
        pattern = re.compile(r'<h2 class="entry-title">.*?(http://oo.xx/\?p=\d+).*?</a></h2>', re.S)
        for match in pattern.finditer(html):
            url = match.group(1)
            print url
            id = re.compile(r'http://oo.xx/\?p=(\d+)').search(url).group(1)
            r_url = requests.get(url)
            r_html = r_url.content
            match = re.compile(r'<div class="entry-content">(.*)</div><!-- \.entry-content -->', re.S).search(r_html)
            if match:
                content = match.group(1).strip()
                db.execute("update typecho_contents_new set text = %s where cid = %s", content, id)
                print id+",DONE"
            else:
                print id+",NO"
    print "DONE"