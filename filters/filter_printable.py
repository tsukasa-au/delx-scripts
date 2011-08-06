#!/usr/bin/env python

import string, sys

while True:
	c = sys.stdin.read(1)
	if c in string.printable:
		sys.stdout.write(c)

