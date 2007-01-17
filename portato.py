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

from portato.constants import VERSION
import sys

if __name__ == "__main__":
	
	uimod = "gtk"

	if len(sys.argv) > 1:
		if sys.argv[1] in ("--help","--version","-h","-v"):
			print """Portato %s
Copyright (C) 2006-2007 René 'Necoro' Neumann
This is free software.  You may redistribute copies of it under the terms of
the GNU General Public License <http://www.gnu.org/licenses/gpl.html>.
There is NO WARRANTY, to the extent permitted by law.

Written by René 'Necoro' Neumann <necoro@necoro.net>""" % VERSION
		else:
			uimod = sys.argv[1]
	
	if uimod == "gtk":
		from portato.gui.gtk import run
	elif uimod == "curses":
		from portato.gui.curses import run
	else:
		print "Unknown interface %s. Correct interfaces are: gtk, curses" % uimod
		sys.exit(1)
	
	run()
