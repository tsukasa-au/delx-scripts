#!/usr/bin/env python

import decorators
import smtplib, email, urllib
import subprocess, sys, optparse
import logging

#### USER CONFIG #####
def getUserConfig():
	smtpServers = (
			SMTPProxy(remoteServer='mail.internode.on.net', domainSuffix='.internode.on.net'),
			SMTPProxy(remoteServer='smtp.usyd.edu.au', domainSuffix='.usyd.edu.au'),
			SMTPProxy(remoteServer='mail.iinet.net.au', domainSuffix='.iinet.net.au'),
			SMTPProxy(remoteServer='mail.netspace.net.au', domainSuffix='.netspace.net.au'),
			SMTPProxy(remoteServer='mail.optusnet.com.au', domainSuffix='.optusnet.com.au'),
			SMTPProxySSH(remoteServer='kagami.tsukasa.net.au'), # Fall back to sending the email via ssh if nothing else
	)

	return smtpServers

#### REAL CODE STARTS HERE ####

class SMTPProxyBase(object):
	def __repr__(self):
		return '%s(%s)' % (self.__class__.__name__, 
				', '.join('%s=%r' % (k, getattr(self, k)) for k in self.__slots__)
				)

class SMTPProxy(SMTPProxyBase):
	__slots__ = (
			'remoteServer',
			'domainSuffix',
			'username',
			'password',
			'useSSL',
		)
	@decorators.logCall
	def __init__(self, remoteServer, domainSuffix, username=None, password=None, useSSL=False):
		self.remoteServer = remoteServer
		self.domainSuffix = domainSuffix

		self.username = username
		self.password = password
		self.useSSL = useSSL

	def doesHandle(self, localhostName):
		'''Determines if this SMTPProxy can be used within this domain'''
		if localhostName is None:
			return False
		else:
			return localhostName.endswith(self.domainSuffix)

	def sendmail(self, fromAddr, toAddrs, message):
		'''
		Actually send the mail.

		Returns true if the mail was successfully send
		'''

		smtp = smtplib.SMTP(self.remoteServer)
		if self.useSSL:
			smtp.starttls()
		if self.username is not None and self.password is not None:
			smtp.login(self.username, self.password)
		smtp.sendmail(fromAddr, toAddrs, message)
		smtp.quit()
		return True

class SMTPProxySSH(SMTPProxyBase):
	__slots__ = ('remoteServer',)
	@decorators.logCall
	def __init__(self, remoteServer):
		self.remoteServer = remoteServer

	def doesHandle(self, *args, **kwargs):
		'''
		Determines if this SMTPProxySSH can be used within this domain.
		Note: This method returns true for all values.
		'''
		return True

	def sendmail(self, fromAddr, toAddrs, message):
		'''
		Actually send the mail.

		Returns true if the mail was successfully send
		'''
		cmdline = ['ssh', self.remoteServer, '/usr/sbin/sendmail', '--']
		cmdline.extend(toAddrs)
		process = subprocess.Popen(cmdline, stdin=subprocess.PIPE)
		process.communicate(message)
		return not bool(process.wait())

def getOptionParser():
	parser = optparse.OptionParser(usage="%prog [options] toAddress1 [toAddress2] ...")
	parser.add_option('--debug',
			action='store_const', dest='debugLevel', const=logging.DEBUG,
			help='Sets the logging level to debug')
	parser.add_option('--warn',
			action='store_const', dest='debugLevel', const=logging.WARNING,
			help='Sets the logging level to warn')
	parser.set_default('debugLevel', logging.ERROR)

	return parser

def main():
	# Get the to addresses
	parser = getOptionParser()
	options, toAddrs = parser.parse_args()
	logging.basicConfig(level=options.debugLevel)
	if not toAddrs:
		parser.error('No to addresses found')

	# Pick a SMTP server
	try:
		host = urllib.urlopen("http://suits.ug.it.usyd.edu.au/myip.php").read().strip()
	except:
		host = None
		logging.exception('Failed to grab our external domain name')

	for smtpProxy in getUserConfig():
		if smtpProxy.doesHandle(host):
			# Got the correct smtpServer
			logging.info('Using the Proxy %r to connect from %s', smtpProxy, host)
			break
	else:
		logging.info('Did not find a proxy to conncet from %s', host)
		return False

	# Get the from address
	message = sys.stdin.read()
	fromAddr = email.message_from_string(message)["from"]
	_, fromAddr = email.utils.parseaddr(fromAddr)

	return smtpProxy.sendmail(fromAddr, toAddrs, message)

if __name__ == "__main__":
	# Specify SMTP servers here
	sys.exit(not main())
