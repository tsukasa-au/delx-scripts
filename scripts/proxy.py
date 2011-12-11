#!/usr/bin/env python

"""
Proxy Utility
-------------

With mode=basic any incoming connections on listen_port will be proxied
to host:port. The proxy will only accept connections from hosts in the
[allowed] section.

With mode=proxy the first two lines of incoming connections must be
'host\nport\n'. Once again only connections from hosts in the [allowed]
section will be accepted. The proxy will connect to host:port and pass
bytes in both directions.

The final mode, mode=interceptor is designed to be combined with a firewall
rule and another instance running mode=proxy on another computer.
Proxies running in interceptor mode listen on all interfaces. They make
connections to the host:port specified in the config file, passing the
'capturedhost\ncapturedport\n' onto the destination. They then pass bytes
in both directions.


Example - Basic Forwarder
-------------------------

Config to forward all packets from port 8000 on localhost to google.com:80
Connections will be accepted from whatever IP address alpha.example.com
and beta.example.com point to.

[proxy]
mode = basic
listen_port = 8000
host = google.com
port = 80

[allowed]
host1 = alpha.example.com
host2 = beta.example.com



Example - Interceptor Proxy Combo
---------------------------------

Capture all packets destined for port 1935 and send them to an interceptor
configured to listen on example.com:9997.
On Linux:
  # iptables -t nat -A PREROUTING -p tcp --dport 1935 
      -j REDIRECT --to-ports 9997
  # iptables -t nat -A OUTPUT -p tcp --dport 1935 
      -j REDIRECT --to-ports 9997

On Mac OS X:
  # ipfw add 50000 fwd 127.0.0.1,9997 tcp from any to any dst-port 1935

Config to forward these connections to proxy.example.com

[proxy]
mode = interceptor
listen_port = 9997
host = proxy.example.com
port = 9997



Config file for proxy.example.com

[proxy]
mode = proxy
listen_port = 9997

[allowed]
host1 = alpha.example.com
host2 = beta.example.com


"""


import asyncore
import ConfigParser
import os
import socket
import struct
import sys
import traceback


if sys.platform == "linux2":
	try:
		socket.SO_ORIGINAL_DST
	except AttributeError:
		# There is a missing const in the socket module... So we will add it now
		socket.SO_ORIGINAL_DST = 80

	def get_original_dest(sock):
		'''Gets the original destination address for connection that has been
		redirected by netfilter.'''
		# struct sockaddr_in {
		#     short            sin_family;   // e.g. AF_INET
		#     unsigned short   sin_port;     // e.g. htons(3490)
		#     struct in_addr   sin_addr;     // see struct in_addr, below
		#     char             sin_zero[8];  // zero this if you want to
		# };
		# struct in_addr {
		#     unsigned long s_addr;  // load with inet_aton()
		# };
		# getsockopt(fd, SOL_IP, SO_ORIGINAL_DST, (struct sockaddr_in *)&dstaddr, &dstlen);

		data = sock.getsockopt(socket.SOL_IP, socket.SO_ORIGINAL_DST, 16)
		_, port, a1, a2, a3, a4 = struct.unpack("!HHBBBBxxxxxxxx", data)
		address = "%d.%d.%d.%d" % (a1, a2, a3, a4)
		return address, port


elif sys.platform == "darwin":
	def get_original_dest(sock):
		'''Gets the original destination address for connection that has been
		redirected by ipfw.'''
		return sock.getsockname()



class Proxy(asyncore.dispatcher):
	def __init__(self, arg):
		if isinstance(arg, tuple):
			asyncore.dispatcher.__init__(self)
			self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
			self.connect(arg)
		else:
			asyncore.dispatcher.__init__(self, arg)
		self.init()

	def init(self):
		self.end = False
		self.other = None
		self.buffer = ""

	def meet(self, other):
		self.other = other
		other.other = self

	def handle_error(self):
		print >>sys.stderr, "Proxy error:", traceback.format_exc()
		self.close()

	def handle_read(self):
		data = self.recv(8192)
		if len(data) > 0:
			self.other.buffer += data

	def handle_write(self):
		sent = self.send(self.buffer)
		self.buffer = self.buffer[sent:]
		if len(self.buffer) == 0 and self.end:
			self.close()

	def writable(self):
		return len(self.buffer) > 0

	def handle_close(self):
		if not self.other:
			return
		print >>sys.stderr, "Proxy closed"
		self.close()
		self.other.end = True
		self.other = None

class ConnectProxy(asyncore.dispatcher):
	def __init__(self, sock):
		asyncore.dispatcher.__init__(self, sock)
		self.buffer = ""

	def handle_error(self):
		print >>sys.stderr, "ConnectProxy error:", traceback.format_exc()
		self.close()

	def handle_read(self):
		self.buffer += self.recv(8192)
		pos1 = self.buffer.find("\n")
		if pos1 < 0:
			return
		host = self.buffer[:pos1].strip()
		pos1 += 1
		pos2 = self.buffer[pos1:].find("\n")
		if pos2 < 0:
			return
		pos2 += pos1
		port = int(self.buffer[pos1:pos2].strip())

		self.buffer = self.buffer[pos2+1:]
		self.done(host, port)

	def handle_write(self):
		pass

	def handle_close(self):
		print >>sys.stderr, "Proxy closed"
		self.close()

	def done(self, host, port):
		print >>sys.stderr, "Forwarding connection", host, port

		# Create server proxy
		server = Proxy((host, port))
		server.buffer = self.buffer

		# Morph and connect
		self.__class__ = Proxy
		self.init()
		server.meet(self)


class BasicForwarder(asyncore.dispatcher):
	def __init__(self, listen_port, host, port, allowed):
		asyncore.dispatcher.__init__(self)
		self.host = host
		self.port = port
		self.allowed = allowed
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind(("", listen_port))
		self.listen(50)
		print >>sys.stderr, "BasicForwarder bound on", listen_port

	def handle_error(self):
		print >>sys.stderr, "BasicForwarder error:", traceback.format_exc()

	def handle_accept(self):
		client_connection, source_addr = self.accept()
		if source_addr[0] not in map(socket.gethostbyname, self.allowed):
			print >>sys.stderr, "Rejected connection from", source_addr
			client_connection.close()
			return

		print >>sys.stderr, "Accepted connection from", source_addr

		# Hook the sockets up to the event loop
		client = Proxy(client_connection)
		server = Proxy((self.host, self.port))
		server.meet(client)

class Forwarder(asyncore.dispatcher):
	def __init__(self, listen_port, allowed):
		asyncore.dispatcher.__init__(self)
		self.allowed = allowed
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind(("", listen_port))
		self.listen(50)
		print >>sys.stderr, "Forwarder bound on", listen_port

	def handle_error(self):
		print >>sys.stderr, "Forwarder error:", traceback.format_exc()

	def handle_accept(self):
		client_connection, source_addr = self.accept()
		if source_addr[0] not in map(socket.gethostbyname, self.allowed):
			print >>sys.stderr, "Rejected connection from", source_addr
			client_connection.close()
			return

		print >>sys.stderr, "Accepted connection from", source_addr
		ConnectProxy(client_connection)

class Interceptor(asyncore.dispatcher):
	def __init__(self, listen_port, host, port):
		asyncore.dispatcher.__init__(self)
		self.host = host
		self.port = port
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind(("0.0.0.0", listen_port))
		self.listen(50)
		print >>sys.stderr, "Interceptor bound on", listen_port

	def handle_error(self):
		print >>sys.stderr, "Interceptor error!", traceback.format_exc()

	def handle_accept(self):
		# Get sockets
		client_connection, source_addr = self.accept()
		dest = get_original_dest(client_connection)
		print >>sys.stderr, "Accepted connection from", source_addr

		# Hook them up to the event loop
		client = Proxy(client_connection)
		server = Proxy((self.host, self.port))
		server.buffer += "%s\n%d\n" % dest
		server.meet(client)


def main(listen_port, host, port, mode, allowed):
	if mode == "basic":
		proxy = BasicForwarder(listen_port, host, port, allowed)
	elif mode == "proxy":
		proxy = Forwarder(listen_port, allowed)
	elif mode == "interceptor":
		proxy = Interceptor(listen_port, host, port)
	else:
		print >>sys.stderr, "Unknown mode:", mode
		return 1
	asyncore.loop()


if __name__ == "__main__":
	try:
		if sys.argv[1] == "-d":
			daemon = True
			config = sys.argv[2]
		else:
			daemon = False
			config = sys.argv[1]
	except (IndexError, ValueError):
		print >>sys.stderr, "Usage: %s [-d] config" % sys.argv[0]
		sys.exit(1)

	try:
		c = ConfigParser.RawConfigParser()
		c.read(config)
	except:
		print >>sys.stderr, "Error parsing config!"
		sys.exit(1)

	def guard(func, message):
		try:
			return func()
		except:
			print >>sys.stderr, "Error:", message
			raise
			sys.exit(1)

	mode = guard(lambda:c.get("proxy", "mode").lower(),
		"mode is a required field")

	listen_port = guard(lambda:c.getint("proxy", "listen_port"),
		"listen_port is a required field")

	if mode in ["basic", "interceptor"]:
		text = "%%s is a required field for mode=%s" % mode
		host = guard(lambda:c.get("proxy", "host"), text % "host")
		port = guard(lambda:c.getint("proxy", "port"), text % "port")
	else:
		host = None
		port = None

	if mode in ["basic", "proxy"]:
		allowed = guard(lambda:c.items("allowed"),
			"[allowed] section is required for mode=%s" % mode)
		allowed = [h for _,h in c.items("allowed")]
	else:
		allowed = None


	if not daemon:
		try:
			main(listen_port, host, port, mode, allowed)
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
				sys.exit(main(listen_port, host, port, mode, allowed))
			except KeyboardInterrupt:
				print
			sys.exit(0)

