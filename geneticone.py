#!/usr/bin/python

#
# File: geneticone.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 Necoro d.M.
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by Necoro d.M. <necoro@necoro.net>

from geneticone.gui import MainWindow
import sys

if __name__ == "__main__":
	if len(sys.argv) > 1 and sys.argv[1] in ("--help","--version","-h","-v"):
		print """Genetic/One SVN-Version
Copyright (C) 2006 Necoro d.M.
This is free software.  You may redistribute copies of it under the terms of
the GNU General Public License <http://www.gnu.org/licenses/gpl.html>.
There is NO WARRANTY, to the extent permitted by law.

Written by Necoro d.M. <necoro@necoro.net>"""
	else:
		m = MainWindow()
		m.main()
