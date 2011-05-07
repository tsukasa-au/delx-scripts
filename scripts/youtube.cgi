#!/usr/bin/env python

import cgi
from lxml.html import document_fromstring
import re
import subprocess
import sys
import urllib


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
			return video_url, extension
			break
		except KeyError:
			continue
	return None, None

def print_filename_header(doc, extension):
	title = doc.xpath("/html/head/title/text()")[0]
	title = re.sub("\s+", " ", title.strip())
	valid_chars = frozenset("\\/-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
	filename = "".join(c for c in title.encode("ascii", "ignore") if c in valid_chars)
	filename += extension
	sys.stdout.write("Content-Disposition: attachment; filename=\"%s\"\r\n" % filename)

def print_stream_file(video_url, silent=True):
	cmd = [
		"curl",
		"--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1",
		"--include",
		video_url,
	]
	if silent:
		cmd.insert(1, "--silent")
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
	block = 32768
	data = p.stdout.read(block)
	data = data[data.find("\n")+1:]
	sys.stdout.write(data)
	while len(data) > 0:
		data = p.stdout.read(block)
		sys.stdout.write(data)
	p.wait()


def main():
	args = cgi.parse()
	try:
		url = args["url"][0]
	except:
		print_form(url="http://www.youtube.com/watch?v=FOOBAR")
		return

	try:
		doc = parse_url(url)
		video_url, extension = get_video_url(doc)
		print_filename_header(doc, extension)
		print_stream_file(video_url, silent=True)
	except Exception, e:
		print_form(
			url=url,
			msg="<p class='error'>Sorry, there was an error. Check your URL?</p>"
		)
		return

if __name__ == "__main__":
	main()

