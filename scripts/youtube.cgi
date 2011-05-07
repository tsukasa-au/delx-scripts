#!/usr/bin/env python

import cgi
from lxml.html import document_fromstring
import os
import re
import shutil
import subprocess
import sys
import urllib


urllib.URLopener.version = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1"

fmt_quality = [
	(38, ".mp4"),  # 4096x3072
	(37, ".mp4"),  # 1920x1080
	(22, ".mp4"),  # 1280x720
	(45, ".webm"), # 1280x720
	(43, ".webm"), # 640x360
	(35, ".flv"),  # 854x480
	(34, ".flv"),  # 640x360
	(18, ".mp4"),  # 480x360
	(5,  ".flv"),  # 400x240
	(17, ".3gp"),  # 176x144
]


def print_form(url="", msg=""):
	print "Content-Type: application/xhtml+xml\r\n\r\n"
	print """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
	<title>delx.net.au - YouTube Scraper</title>
	<link rel="stylesheet" type="text/css" href="/style.css"/>
	<style type="text/css">
		input[type="text"] {
			width: 100%;
		}
		.error {
			color: red;
		}
	</style>
</head>
<body>
	<h1>delx.net.au - YouTube Scraper</h1>
	{0}
	<form action="" method="get">
	<p>This page will let you easily download YouTube videos to watch offline. It
	will automatically grab the highest quality version.</p>
	<div><input type="text" name="url" value="{1}"/></div>
	<div><input type="submit" value="Download!"/></div>
	</form>
	<p>Tip! Use this bookmarklet: <a href="javascript:(function(){window.location='http://delx.net.au/utils/youtube.cgi?url='+escape(location);})()">YouTube Download</a>
	to easily download videos. Right-click the link and add it to bookmarks,
	then when you're looking at a YouTube page select that bookmark from your
	browser's bookmarks menu to download the video straight away.</p>
</body>
</html>
""".replace("{0}", msg).replace("{1}", url)

def parse_url(url):
	f = urllib.urlopen(url)
	doc = document_fromstring(f.read())
	f.close()
	return doc

def get_video_url(doc):
	embed = doc.xpath("//embed")[0]
	flashvars = embed.attrib["flashvars"]
	flashvars = cgi.parse_qs(flashvars)
	fmt_url_map = {}
	for pair in flashvars["fmt_url_map"][0].split(","):
		key, value = pair.split("|")
		key = int(key)
		fmt_url_map[key] = value
	for fmt, extension in fmt_quality:
		try:
			video_url = fmt_url_map[fmt]
			break
		except KeyError:
			continue
	else:
		return None, None, None

	title = doc.xpath("/html/head/title/text()")[0]
	title = re.sub("\s+", " ", title.strip())
	valid_chars = frozenset("-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
	filename = "".join(c for c in title.encode("ascii", "ignore") if c in valid_chars)
	filename += extension

	return video_url, filename

def cgimain():
	args = cgi.parse()
	try:
		url = args["url"][0]
	except:
		print_form(url="http://www.youtube.com/watch?v=FOOBAR")
		return

	try:
		doc = parse_url(url)
		video_url, filename = get_video_url(doc)
		data = urllib.urlopen(video_url)
		httpinfo = data.info()
		sys.stdout.write("Content-Disposition: attachment; filename=\"%s\"\r\n" % filename)
		sys.stdout.write("Content-Length: %s\r\n" % httpinfo.getheader("Content-Length"))
		sys.stdout.write("\r\n")
		shutil.copyfileobj(data, sys.stdout)
		data.close()
	except Exception, e:
		print_form(
			url=url,
			msg="<p class='error'>Sorry, there was an error. Check your URL?</p>"
		)
		return

def main():
	try:
		url = sys.argv[1]
	except:
		print >>sys.stderr, "Usage: %s http://youtube.com/watch?v=FOOBAR" % sys.argv[0]
		sys.exit(1)
	doc = parse_url(url)
	video_url, filename = get_video_url(doc)
	data = urllib.urlopen(video_url)
	outfile = open(filename, "w")
	shutil.copyfileobj(data, outfile)
	data.close()
	outfile.close()


if __name__ == "__main__":
	if os.environ.has_key("SCRIPT_NAME"):
		cgimain()
	else:
		main()

