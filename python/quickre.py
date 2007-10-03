# Copyright 2007 James Bunton <jamesbunton@fastmail.fm>
# Licensed for distribution under the GPL version 2, check COPYING for details
# Quicker, easier regular expressions

import re

class RE(object):
	def __init__(self, regex):
		self.regex = re.compile(regex)
	
	def __eq__(self, s):
		assert isinstance(s, basestring)
		return self.regex.search(s)
	
	def __ne__(self, s):
		return not self == s

