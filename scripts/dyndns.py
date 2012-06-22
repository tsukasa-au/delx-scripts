#!/usr/bin/env python

from datetime import datetime
import os
import subprocess
import sys
import re


def increment_serial(line):
	current_serial = re.search(R"\b\d\d*\b", line).group(0)

	current = int(current_serial)
	current_num = current % 100
	current_date = (current - current_num) / 100
	new_date = int(datetime.now().strftime("%Y%m%d"))
	if current_date == new_date:
		next_num = current_num + 1
	else:
		next_num = 0

	if next_num >= 100:
		raise ValueError("Too many serial changes today!")
	new_serial = str(new_date) + str(next_num).zfill(2)
	line = line.replace(current_serial, new_serial)

	return line

def replace_ip(line):
	source_ip, source_port, dest_ip, dest_port = os.environ["SSH_CONNECTION"].split()
	line = re.sub(R"\b\d\d?\d?\.\d\d?\d?\.\d\d?\d?\.\d\d?\d?\b", source_ip, line)
	return line


def main(live, zonefile, dnslabel):
	f = open(zonefile)
	out = []
	for line in f:
		if line.find("Serial") >= 0:
			out.append(increment_serial(line))
		elif line.find("DYNDNS") >= 0 and line.find("bnet") >= 0:
			out.append(replace_ip(line))
		else:
			out.append(line)

	f.close()

	if live:
		outf = open(zonefile, "w")
		outf.writelines(out)
		outf.close()
		subprocess.check_call(["sudo", "/etc/init.d/bind9", "reload"])
	else:
		sys.stdout.writelines(out)


if __name__ == "__main__":
	live = False
	try:
		i = 1
		if sys.argv[1] == "live":
			live = True
			i = 2
		zonefile = sys.argv[i]
		dnslabel = sys.argv[i+1]
	except:
		print >>sys.stderr, "Usage: %s [go] zonefile dnslabel" % sys.argv[0]
		sys.exit(1)

	main(live, zonefile, dnslabel)


