#!/usr/bin/env python

import asyncore
import os
import socket
import sys

class Proxy(asyncore.dispatcher):
	def __init__(self, sock):
		asyncore.dispatcher.__init__(self, sock)
		self.other = None
		self.towrite = ""
	
	def meet(self, other):
		self.other = other
		other.other = self
	
	def handle_error(self):
		print >>sys.stderr, "Connection closed..."
		self.handle_close()

	def handle_read(self):
		data = self.recv(8192)
		self.other.towrite += data
	
	def handle_write(self):
		sent = self.send(self.towrite)
		self.towrite = self.towrite[sent:]
	
	def handle_close(self):
		if not self.other:
			return
		self.other.close()
		self.close()
		self.other = None

class Forwarder(asyncore.dispatcher):
	def __init__(self, host, port):
		asyncore.dispatcher.__init__(self)
		self.host = host
		self.port = port
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.bind(("", port))
		self.listen(5)
	
	def handle_error(self):
		print >>sys.stderr, "Connection error!"
	
	def handle_accept(self):
		# Get sockets
		clientConnection, addr = self.accept()
		print >>sys.stderr, "Accepted connection from", addr
		serverConnection = socket.socket()
		serverConnection.connect((self.host, self.port))

		# Hook them up to the event loop
		client = Proxy(clientConnection)
		server = Proxy(serverConnection)
		server.meet(client)

def main(host, port):
	proxy = Forwarder(host, port)
	asyncore.loop()

if __name__ == "__main__":
	try:
		if sys.argv[1] == "-d":
			daemon = True
			host, port = sys.argv[2:]
		else:
			host, port = sys.argv[1:]
			daemon = False
		port = int(port)
	except ValueError:
		print >> sys.stderr, "Usage: %s [-d] host port" % sys.argv[0]
		sys.exit(1)

	if not daemon:
		try:
			main(host, port)
		except KeyboardInterrupt:
			print
	else:
		sys.stdin.close()
		sys.stdout.close()
		sys.stderr.close()
		sys.stdin = open("/dev/null")
		sys.stdout = open("/dev/null")
		sys.stderr = open("/dev/null")

		if os.fork() == 0:
			# We are the child
			try:
				main(host, port)
			except KeyboardInterrupt:
				print
			sys.exit(0)

