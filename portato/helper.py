# -*- coding: utf-8 -*-
#
# File: portato/helper.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net> et.al.

import traceback, os.path

DEBUG = True

def set_debug (d):
	"""Sets the global DEBUG variable. Do not set it by your own - always use this function.

	@param d: True to enable debugging; False otherwise
	@type d: boolean"""

	global DEBUG
	DEBUG = d

def debug(*args, **kwargs):
	"""Prints a debug message including filename and lineno.
	A variable number of positional arguments are allowed.

	If debug(obj0, obj1, obj2) is called, the text part of the output 
	looks like the output from print obj0, obj1, obj2.
	
	If you pass the optional keyword-argument "name", it is used for the function-name instead of the original one."""

	
	if not DEBUG : return
	
	stack = traceback.extract_stack()
	minus = -2
	if "minus" in kwargs:
		minus = minus - kwargs["minus"]
	a, b, c, d = stack[minus]
	a = os.path.basename(a)
	out = []
	for obj in args:
		out.append(str(obj))
	text = ' '.join(out)
	if "name" in kwargs:
		text = 'In %s (%s:%s): %s' % (kwargs["name"], a, b, text)
	else:
		text = 'In %s (%s:%s): %s' % (c, a, b, text)
	
	text = "***DEBUG*** %s ***DEBUG***" % text
	
	if "file" in kwargs:
		f = open(kwargs["file"], "a+")
		f.write(text+"\n")
		f.close()
	else:
		print text

def am_i_root ():
	"""Returns True if the current user is root, False otherwise.
	@rtype: boolean"""
	if os.getuid() == 0:
		return True
	else:
		return False

def unique_array(s):
	"""Stolen from portage_utils:
	lifted from python cookbook, credit: Tim Peters
	Return a list of the elements in s in arbitrary order, sans duplicates"""
	n = len(s)
	# assume all elements are hashable, if so, it's linear
	try:
		return list(set(s))
	except TypeError:
		pass

	# so much for linear.  abuse sort.
	try:
		t = list(s)
		t.sort()
	except TypeError:
		pass
	else:
		assert n > 0
		last = t[0]
		lasti = i = 1
		while i < n:
			if t[i] != last:
				t[lasti] = last = t[i]
				lasti += 1
			i += 1
		return t[:lasti]

	# blah.	 back to original portage.unique_array
	u = []
	for x in s:
		if x not in u:
			u.append(x)
	return u
