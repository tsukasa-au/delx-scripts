#!/usr/bin/env python

import unittest

from stringinterpolate import string_interpolate

class TestInterpolate(unittest.TestCase):
	def test1(self):
		format = "%(a)s %(b)s"
		data = {"a": "hello", "b": "world"}
		result = list(string_interpolate(format, data))
		expected = ["hello world"]
		self.assertEquals(result, expected)
	
	def test2(self):
		format = "%(a)s %(b)s"
		data = {"a": ["hello", "hello2"], "b": ["world", "world2"]}
		result = list(string_interpolate(format, data))
		expected = ["hello world", "hello world2", "hello2 world", "hello2 world2"]
		self.assertEquals(result, expected)
	
	def test3(self):
		format = "%(a)s %(b)s"
		data = {"a": ["hello", "hello2"], "b": "world"}
		result = list(string_interpolate(format, data))
		expected = ["hello world", "hello2 world"]
		self.assertEquals(result, expected)

if __name__ == "__main__":
	unittest.main()

