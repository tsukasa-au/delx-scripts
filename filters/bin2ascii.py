#!/usr/bin/env python

import binascii, sys

if len(sys.argv) == 2:
	input = sys.argv[1]
else:
	input = sys.stdin.read()

print binascii.unhexlify(hex(int(input, 2))[2:])
