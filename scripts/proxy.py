#!/usr/bin/env python

# Sample config file:

# [proxy]
# listen_port = 8000
# host = google.com
# port = 80
# 
# [allowed]
# host1 = delx.cjb.net
# host2 = 333.333.333.333


import asyncore
import ConfigParser
import os
import socket
import sys

class Proxy(asyncore.dispatcher):
	def __init__(self, sock):
		asyncore.dispatcher.__init__(self, sock)
		self.other = None
		self.buffer = ""
	
	def meet(self, other):
		self.other = other
		other.other = self
	
	def handle_error(self):
		print >>sys.stderr, "Connection closed..."
		self.handle_close()

	def handle_read(self):
		data = self.recv(8192)
		self.other.buffer += data
	
	def handle_write(self):
		sent = self.send(self.buffer)
		self.buffer = self.buffer[sent:]
	
	def handle_close(self):
		if not self.other:
			return
		self.other.close()
		self.close()
		self.other = None

class Forwarder(asyncore.dispatcher):
	def __init__(self, listen_port, host, port, allowed):
		asyncore.dispatcher.__init__(self)
		self.host = host
		self.port = port
		self.allowed = allowed
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.bind(("", listen_port))
		self.listen(5)
	
	def handle_error(self):
		print >>sys.stderr, "Connection error!", sys.exc_info()
	
	def handle_accept(self):
		client_connection, (addr, port) = self.accept()
		if addr not in map(socket.gethostbyname, self.allowed):
			print >>sys.stderr, "Rejected connection from", addr
			client_connection.close()
			return

		print >>sys.stderr, "Accepted connection from", addr, port
		server_connection = socket.socket()
		server_connection.connect((self.host, self.port))

		# Hook the sockets up to the event loop
		client = Proxy(client_connection)
		server = Proxy(server_connection)
		server.meet(client)

def main(listen_port, host, port, allowed):
	proxy = Forwarder(listen_port, host, port, allowed)
	asyncore.loop()

if __name__ == "__main__":
	try:
		if sys.argv[1] == "-d":
			daemon = True
			config = sys.argv[2]
		else:
			daemon = False
			config = sys.argv[1]
	except ValueError:
		print >>sys.stderr, "Usage: %s [-d] config" % sys.argv[0]
		sys.exit(1)

	try:
		c = ConfigParser.RawConfigParser()
		c.read(config)
		listen_port = c.getint("proxy", "listen_port")
		host = c.get("proxy", "host")
		port = c.getint("proxy", "port")
		allowed = c.items("allowed")
		allowed = [h for _,h in c.items("allowed")]
	except:
		print >>sys.stderr, "Error parsing config!"
		sys.exit(1)

	if not daemon:
		try:
			main(listen_port, host, port, allowed)
		except KeyboardInterrupt:
			print
	else:
		os.close(0)
		os.close(1)
		os.close(2)
		os.open("/dev/null", os.O_RDONLY)
		os.open("/dev/null", os.O_RDWR)
		os.dup(1)

		if os.fork() == 0:
			# We are the child
			try:
				main(listen_port, host, port, allowed)
			except KeyboardInterrupt:
				print
			sys.exit(0)

