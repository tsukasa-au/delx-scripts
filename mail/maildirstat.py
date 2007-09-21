#!/usr/bin/env python

import os, os.path, sys
j = os.path.join

def checkMailbox(mailbox):
	""" Ensure that mailbox is a maildir directory """
	if not (os.path.isdir(mailbox) and
	        os.path.isdir(j(mailbox, "cur")) and
	        os.path.isdir(j(mailbox, "new")) and
	        os.path.isdir(j(mailbox, "tmp"))):
		print >> sys.stderr, "Error! Not a maildir mailbox."
		sys.exit(1)
	
def extractFlags(messages):
	""" Extract the flags from the messages """
	return [m.rsplit(":", 1)[1].split(",")[1] for m in messages]

def main(mailbox, format):
	checkMailbox(mailbox)

	# Reuse the directory listing
	curList = extractFlags(os.listdir(j(mailbox, "cur")))

	# Get the new messages
	newCount = len(os.listdir(j(mailbox, "new")))
	newCount += len([m for m in curList if "N" in m])

	# Get the unread messages
	unreadCount = len([m for m in curList if "S" not in m])

	# Format it nicely
	format = format.replace("\\n", "\n")
	mailbox = os.path.basename(mailbox)
	sys.stdout.write(format % (mailbox, newCount, unreadCount))

if __name__ == "__main__":
	try:
		mailbox = sys.argv[1]
		format = sys.argv[2]
	except IndexError:
		print >> sys.stderr, "Usage: %s mailbox format" % sys.argv[0]
		sys.exit(1)

	main(mailbox, format)

