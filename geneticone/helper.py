# -*- coding: utf-8 -*-
#
# File: geneticone/helper.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
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
	a, b, c, d = stack[-2]
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
	
	print text

def am_i_root ():
	"""Returns True if the current user is root, False otherwise.
	@rtype: boolean"""
	if os.getuid() == 0:
		return True
	else:
		return False
