#!/usr/bin/env python

import csv
import sys

rows = list(csv.reader(sys.stdin))
column_widths = list(max((len(str(cell))) for cell in column) for column in zip(*rows))
for row in rows:
	for width, cell in zip(column_widths, row):
		print str(cell).ljust(width),
	print
