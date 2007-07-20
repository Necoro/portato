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

from portato.constants import VERSION, FRONTENDS, STD_FRONTEND, XSD_LOCATION
from optparse import OptionParser
import sys

def get_frontend_list ():
	return ", ".join(["'%s'" % x for x in FRONTENDS])

def main ():

	# build the parser
	desc = """Portato - A Portage GUI."""
	usage = "%prog [options] [frontend]"
	vers =  "%%prog v. %s" % VERSION

	parser = OptionParser(version = vers, prog = "Portato", description = desc, usage = usage)
	
	parser.add_option("--check", action = "store_true", dest = "check", default = False,
			help = "runs pychecker (should only be used by developers)")
	
	parser.add_option("-f", "--frontend", action = "store", choices = FRONTENDS, default = STD_FRONTEND, dest = "frontend",
			help = "the frontend to use - possible values are: %s [default: %%default]" % get_frontend_list())

	parser.add_option("-e", "--ebuild", action = "store", dest = "ebuild",
			help = "opens the ebuild viewer instead of launching Portato")

	parser.add_option("-x", "--validate", action = "store", dest = "validate", metavar="PLUGIN",
			help = "validates the given plugin xml instead of launching Portato")

	# run parser
	(options, args) = parser.parse_args()

	# evaluate parser's results
	if options.check: # run pychecker
		import os
		os.environ['PYCHECKER'] = "--limit 50"
		import pychecker.checker
	
	if len(args): # additional arguments overwrite given frontend
		arg = args[0]
		if arg not in FRONTENDS:
			print "Unknown frontend '%s'. Correct frontends are: %s" % (arg, get_frontend_list())
			sys.exit(2)
		else:
			options.frontend = arg

	try:
		exec ("from portato.gui.%s import run, show_ebuild" % options.frontend)
	except ImportError, e:
		print "'%s' should be installed, but cannot be imported. This is definitly a bug. (%s)" % (options.frontend, e[0])
		sys.exit(1)

	if options.ebuild:
		show_ebuild(options.ebuild)
	elif options.validate:
		from lxml import etree
		if etree.XMLSchema(file = XSD_LOCATION).validate(etree.parse(options.validate)):
			print "Passed validation."
			return
		else:
			print "Verification failed."
			sys.exit(3)
	else:
		run()

if __name__ == "__main__":
	main()
