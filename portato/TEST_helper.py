#!/usr/bin/python

from __future__ import absolute_import

import unittest
from . import helper

class HelperTest (unittest.TestCase):

	def testFlatten(self):
		list = [[1,2],[3,4],[[5],[6,7,8], 9]]
		flist = helper.flatten(list)
		self.assertEqual(flist, [1,2,3,4,5,6,7,8,9], "List not flattend correctly.")

	def testUniqueArray(self):

		def equal (l1, l2):
			for i in l1:
				if i not in l2:
					return False
				l2.remove(i)
			return True

		list1 = [1,4,5,2,1,7,9,11,2,4,7,12]
		result1 = [1,4,5,2,7,9,11,12]

		list2 = [[x] for x in list1]
		result2 = [[x] for x in result1]

		self.assert_(equal(helper.unique_array(list1), result1), "Make hashable list unique does not work.")
		self.assert_(equal(helper.unique_array(list2), result2), "Make unhashable list unique does not work.")

if __name__ == "__main__":
	unittest.main()
