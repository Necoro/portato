#
# File: geneticone/helper.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 Necoro d.M.
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by Necoro d.M. <necoro@necoro.net> et.al.

import traceback, textwrap, os.path

def debug(*args, **kwargs):
	"""Prints a debug message including filename and lineno.
	A variable number of positional arguments are allowed.
	If lineno(obj0, obj1, obj2) is called, the text part of the output 
	looks like the output from print obj0, obj1, obj2 .
	The optional keyword "wrap" causes the message to be line-wrapped. The
	argument to "wrap" should be "1" or "True". "name" is another optional
	keyword parameter.

	(This function is adapted from Edward Jones as published under: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/279155)"""
	
	stack = traceback.extract_stack()
	a, b, c, d = stack[-2]
	a = os.path.basename(a)
	out = []
	for obj in args:
		out.append(str(obj))
	text = ' '.join(out)
	if "name" in kwargs:
		text = 'In %s (%s:%s) %s:' % (kwargs["name"], a, b, text)
	else:
		text = 'In %s (%s:%s) %s:' % (c, a, b, text)
	#if wrap:
	#	text = textwrap.fill(text)
	
	text = "***DEBUG*** %s ***DEBUG***" % text
	
	print text

def am_i_root ():
	"""Returns True if the current user is root, False otherwise."""
	if os.getuid() == 0:
		return True
	else:
		return False
