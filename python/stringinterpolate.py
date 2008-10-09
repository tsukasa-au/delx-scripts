#!/usr/bin/env python

__all__ = ["string_interpolate"]

def string_interpolate(format, data):
	fakeData = KeyDetect()
	format % fakeData
	keys = fakeData.keys

	for d in combinations(data, keys):
		yield format % d

def myiter(obj):
	if isinstance(obj, basestring):
		return [obj]
	else:
		return obj

def combinations(data, keys):
	key = keys[0]
	keys = keys[1:]

	if len(keys) == 0:
		for val in myiter(data[key]):
			yield {key: val}

	else:
		for val in myiter(data[key]):
			for d in combinations(data, keys):
				d[key] = val
				yield d


class KeyDetect(object):
	def __init__(self):
		self.keys = []
	def __getitem__(self, key):
		self.keys.append(key)
		return ""

