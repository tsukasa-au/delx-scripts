#!/usr/bin/env python

import fcntl
import os
import subprocess
import sys

if not sys.platform.startswith("linux"):
	print >>sys.stderr, "Sorry, this tool requires Linux"
	sys.exit(1)

try:
	search_usb_id = sys.argv[1].lower()
except IndexError:
	print >>sys.stderr, "Usage: %s vendorid:devid" % sys.argv[0]
	print >>sys.stderr, "\nThis tool will reset all USB devices with the given ID (eg 1f4d:a803)"
	sys.exit(1)


USBDEVFS_RESET = 21780

os.umask(0007)

p = subprocess.Popen(["lsusb"], stdout=subprocess.PIPE)
for line in p.stdout:
	line = line.split()
	usb_id = line[5].lower()
	if usb_id != search_usb_id:
		continue
	bus = line[1]
	dev = line[3].replace(":", "")

	filename = "/dev/bus/usb/%s/%s" % (bus, dev)
	print "Resetting", filename, "...",
	fd = os.open(filename, os.O_WRONLY)
	ret = fcntl.ioctl(fd, USBDEVFS_RESET, 0)
	if ret < 0:
		print >>sys.stderr, "\nError in ioctl:", ret
		sys.exit(1)
	os.close(fd)
	print "done"

