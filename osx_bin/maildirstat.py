#!/usr/bin/env python

import os, os.path, sys
import kqueue
j = os.path.join
sep = os.path.sep

def watchDirectories(directories):
	""" Given a list of directories to monitor, returns a function which when
	called will sleep until a directory changes, and then return a list of
	changed directories.
	"""
	def doWatch():
		while True:
			changed = []
			for event in kqueue.kevent(kq, events, 10, None):
				changed.append(directories[dirfds.index(event.ident)])
			return changed

	# Open all the directories
	dirfds = []
	for directory in directories:
		dirfds.append(os.open(directory, os.O_RDONLY))

	# Set up the kqueue events
	events = []
	filter = kqueue.EV_ADD | kqueue.EV_CLEAR | kqueue.EV_ENABLE
	fflags = kqueue.NOTE_WRITE | kqueue.NOTE_DELETE | kqueue.NOTE_EXTEND
	for fd in dirfds:
		e=kqueue.Event(fd, kqueue.EVFILT_VNODE, filter, fflags=fflags, data=fd)
		events.append(e)

	# Give back a function pointer
	kq = kqueue.kqueue()
	return doWatch

def clear():
	""" Clears the screen """
	os.system("clear")

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

def maildirStat(mailbox):
	""" Returns newCount, unreadCount for the given maildir mailbox """
	checkMailbox(mailbox)

	# Reuse the directory listing
	curList = extractFlags(os.listdir(j(mailbox, "cur")))

	# Get the new messages
	newCount = len(os.listdir(j(mailbox, "new")))
	newCount += len([m for m in curList if "N" in m])

	# Get the unread messages
	unreadCount = len([m for m in curList if "S" not in m])

	return newCount, unreadCount

def multiStat(mailboxes, counts):
	for mailbox in mailboxes:
		counts[mailbox] = maildirStat(mailbox)

def printCounts(mailboxes, counts):
	""" Prints the counts to the screen ordered """
	clear()
	for mailbox in mailboxes:
		newCount, unreadCount = counts[mailbox]
		mailbox = mailbox.rsplit("/", 1)[-1]
		print "%s:\n\t%d\t%d\n" % (mailbox, newCount, unreadCount)

def main(mailboxes):
	""" Stat all the mailboxes and then watch for changes """
	counts = {}
	multiStat(mailboxes, counts)
	printCounts(mailboxes, counts)

	watcher = watchDirectories([j(m, "cur") for m in mailboxes] +
	                           [j(m, "new") for m in mailboxes])
	while True:
		changed = watcher()
		changed = [sep.join(d.split(os.path.sep)[:-1]) for d in changed]
		changed = list(set(changed))
		multiStat(changed, counts)
		printCounts(mailboxes, counts)


if __name__ == "__main__":
	try:
		mailboxes = sys.argv[1:]
	except IndexError:
		print >> sys.stderr, "Usage: %s mailbox [mailbox ...]" % sys.argv[0]
		sys.exit(1)

	try:
		main(mailboxes)
	except KeyboardInterrupt:
		print

