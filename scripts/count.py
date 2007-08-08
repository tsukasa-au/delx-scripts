#!/usr/bin/env python
# Print a line count. Given an input file like this:
# apple
# apple
# banana
# carrot
# apple
#
# Your output will be
# apple 2
# banana 1
# carrot 1
# apple 1

import sys

last = ""
count = 0
for line in sys.stdin:
	line = line.strip()
	if line == last:
		count += 1
	else:
		if last:
			print last, count
		last = line
		count = 1

print last, count

