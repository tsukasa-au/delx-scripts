#!/usr/bin/env python

# Specify SMTP servers here
smtpServerList = [
(".internode.on.net", "mail.internode.on.net"),
(".usyd.edu.au", "mail.usyd.edu.au"),
(".iinet.net.au", "mail.iinet.net.au"),
(".netspace.net.au", "mail.netspace.net.au"),
(".optusnet.com.au", "mail.optusnet.com.au")
]



import email, email.utils, smtplib, sys, urllib

# Get the to addresses
toAddrs = sys.argv[1:]
try:
	toAddrs.remove("--")
except ValueError:
	pass
if len(toAddrs) == 0 or filter(lambda to: to.startswith("-"), toAddrs):
	# Either no addresses, or an unknown parameter
	print >>sys.stderr, "Usage: %s toAddr ..." % sys.argv[0]
	sys.exit(1)

# Pick a SMTP server
try:
	host = urllib.urlopen("http://suits.ug.it.usyd.edu.au/myip.php").read().strip()
	for hostMatch, smtpServer in smtpServerList:
		if host.endswith(hostMatch):
			# Got the correct smtpServer
			break
	else:
		raise Exception, "No match for hostname: %s" % host
except Exception, e:
	print >>sys.stderr, "Error! Couldn't pick an SMTP server"
	print >>sys.stderr, e
	sys.exit(1)

# Get the from address
message = sys.stdin.read()
fromAddr = email.message_from_string(message)["from"]
fromAddr = email.utils.parseaddr(fromAddr)[1]

# Send the email
smtp = smtplib.SMTP(smtpServer)
smtp.sendmail(fromAddr, toAddrs, message)
smtp.quit()

