#!/usr/bin/env python

import cookielib
import cgi
import itertools
import json
from lxml.html import document_fromstring, tostring
import os
import re
import resource
import shutil
import subprocess
import sys
import urllib
import urllib2
import urlparse


MAX_MEMORY_BYTES = 128 * 1024*1024
USER_AGENT = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1"

MIMETYPES = {
	"video/mp4": "mp4",
	"video/x-flv": "flv",
	"video/3gpp": "3gp",
}

QUALITIES = {
	"large": 3,
	"medium": 2,
	"small": 1,
}


class VideoUnavailable(Exception):
	pass

def print_form(url="", msg=""):
	script_url = "http://%s%s" % (os.environ["HTTP_HOST"], os.environ["REQUEST_URI"])
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
	<p>Tip! Use this bookmarklet: <a href="javascript:(function(){window.location='{2}?url='+escape(location);})()">YouTube Download</a>
	to easily download videos. Right-click the link and add it to bookmarks,
	then when you're looking at a YouTube page select that bookmark from your
	browser's bookmarks menu to download the video straight away.</p>
</body>
</html>
""".replace("{0}", msg).replace("{1}", url).replace("{2}", script_url)

cookiejar = cookielib.CookieJar()
urlopener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
referrer = ""

def urlopen(url):
	global referrer
	req = urllib2.Request(url)
	if referrer:
		req.add_header("Referer", referrer)
	referrer = url
	req.add_header("User-Agent", USER_AGENT)
	return urlopener.open(req)

def parse_url(url):
	f = urlopen(url)
	doc = document_fromstring(f.read())
	f.close()
	return doc

def append_to_qs(url, params):
	r = list(urlparse.urlsplit(url))
	qs = urlparse.parse_qs(r[3])
	qs.update(params)
	r[3] = urllib.urlencode(qs, True)
	url = urlparse.urlunsplit(r)
	return url

def convert_from_old_itag(player_config):
	url_data = urlparse.parse_qs(player_config["args"]["url_encoded_fmt_stream_map"])
	url_data["url"] = []
	for itag_url in url_data["itag"]:
		pos = itag_url.find("url=")
		url_data["url"].append(itag_url[pos+4:])
	player_config["args"]["url_encoded_fmt_stream_map"] = urllib.urlencode(url_data, True)

def get_player_config(doc):
	player_config = None
	for script in doc.xpath("//script"):
		if not script.text:
			continue
		for line in script.text.split("\n"):
			if "yt.playerConfig =" in line:
				p1 = line.find("=")
				p2 = line.rfind(";")
				if p1 >= 0 and p2 > 0:
					return json.loads(line[p1+1:p2])
			if "'PLAYER_CONFIG': " in line:
				p1 = line.find(":")
				if p1 >= 0:
					player_config = json.loads(line[p1+1:])
					convert_from_old_itag(player_config)
					return player_config

def get_best_video(player_config):
	url_data = urlparse.parse_qs(player_config["args"]["url_encoded_fmt_stream_map"])
	url_data = itertools.izip_longest(
		url_data["url"],
		url_data["type"],
		url_data["quality"],
		url_data.get("sig", []),
	)
	best_url = None
	best_quality = None
	best_extension = None
	for video_url, mimetype, quality, signature in url_data:
		mimetype = mimetype.split(";")[0]
		if mimetype not in MIMETYPES:
			continue
		extension = "." + MIMETYPES[mimetype]
		quality = QUALITIES.get(quality.split(",")[0], -1)
		if best_quality is None or quality > best_quality:
			if signature:
				video_url = append_to_qs(video_url, {"signature": signature})
			best_url = video_url
			best_quality = quality
			best_extension = extension

	return best_url, best_extension

def get_video_url(doc):
	unavailable = doc.xpath("//div[@id='unavailable-message']/text()")
	if unavailable:
		raise VideoUnavailable(unavailable[0].strip())

	player_config = get_player_config(doc)
	if not player_config:
		raise VideoUnavailable("Could not find video URL")

	video_url, extension = get_best_video(player_config)
	if not video_url:
		return None, None

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
		data = urlopen(video_url)
		httpinfo = data.info()
		sys.stdout.write("Content-Disposition: attachment; filename=\"%s\"\r\n" % filename)
		sys.stdout.write("Content-Length: %s\r\n" % httpinfo.getheader("Content-Length"))
		sys.stdout.write("\r\n")
		shutil.copyfileobj(data, sys.stdout)
		data.close()
	except VideoUnavailable, e:
		print_form(
			url=url,
			msg="<p class='error'>Sorry, there was an error: %s</p>" % cgi.escape(e.message)
		)
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
	data = urlopen(video_url)
	outfile = open(filename, "w")
	shutil.copyfileobj(data, outfile)
	data.close()
	outfile.close()


if __name__ == "__main__":
	resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
	if os.environ.has_key("SCRIPT_NAME"):
		cgimain()
	else:
		main()

