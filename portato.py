#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# File: portato.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from portato.constants import VERSION, FRONTENDS, STD_FRONTEND
import sys

def main ():
	uimod = STD_FRONTEND

	for arg in sys.argv[1:]:
		if arg in ("--help","--version","-h","-v"):
			print """Portato %s
Copyright (C) 2006-2007 René 'Necoro' Neumann
This is free software.  You may redistribute copies of it under the terms of
the GNU General Public License <http://www.gnu.org/licenses/gpl.html>.
There is NO WARRANTY, to the extent permitted by law.

Written by René 'Necoro' Neumann <necoro@necoro.net>""" % VERSION
			sys.exit(0)
		
		if arg == "--check": # run pychecker
			import os
			os.environ['PYCHECKER'] = "--limit 50"
			import pychecker.checker
			continue
		
		uimod = arg
		break

	if uimod in FRONTENDS:
		try:
			exec ("from portato.gui.%s import run" % uimod)
		except ImportError, e:
			print "'%s' should be installed, but cannot be imported. This is definitly a bug. (%s)" % (uimod, e[0])
			sys.exit(1)
	else:
		print ("Unknown interface '%s'. Correct interfaces are:" % uimod) ,
		for u in FRONTENDS:
			print u ,
		print
		sys.exit(1)
	
	run()

if __name__ == "__main__":
	main()
