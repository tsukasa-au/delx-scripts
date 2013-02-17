#!/usr/bin/python

import cherrypy
import os
import sys
import webbrowser

class Listener(object):
	@cherrypy.expose
	def firefox(self, url):
		print "Loading:", url
		webbrowser.open(url)
		raise cherrypy.HTTPRedirect(url, status=303)

def do_fork():
	pid = os.fork()
	if pid < 0:
		print >>sys.stderr, "Unable to fork!"
		sys.exit(1)
	if pid != 0:
		sys.exit(0)

def main(fork):
	if fork:
		do_fork()
	cherrypy.tree.mount(Listener())
	cherrypy.server.socket_host = "0.0.0.0"
	cherrypy.server.socket_port = 8080
	cherrypy.engine.start()

if __name__ == "__main__":
	fork = False
	if len(sys.argv) != 1:
		if sys.argv[1] == "--fork":
			fork = True
		else:
			print >>sys.stderr, "Usage: %s [--fork]" % sys.argv[0]
			sys.exit(1)
	main(fork)

