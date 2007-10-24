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

from __future__ import with_statement, absolute_import

import sys, os, subprocess
import gettext, locale
from optparse import OptionParser, SUPPRESS_HELP

try:
	import shm_wrapper as shm
except ImportError:
	from portato.shm import shm_wrapper as shm

from portato import get_listener
from portato.constants import VERSION, FRONTENDS, STD_FRONTEND, XSD_LOCATION, LOCALE_DIR, APP, SU_COMMAND

def get_frontend_list ():
	return ", ".join(["'%s'" % x for x in FRONTENDS])

def main ():
	# set gettext stuff
	locale.setlocale(locale.LC_ALL, '')
	gettext.bindtextdomain(APP, LOCALE_DIR)
	gettext.textdomain(APP)
	_ = gettext.lgettext

	# build the parser
	desc = "Portato - A Portage GUI."
	usage = "%prog [options] [frontend]"
	vers =  "%%prog v. %s" % VERSION

	parser = OptionParser(version = vers, prog = "Portato", description = desc, usage = usage)
	
	parser.add_option("--check", action = "store_true", dest = "check", default = False,
			help = _("runs pychecker (should only be used by developers)"))
	
	parser.add_option("-f", "--frontend", action = "store", choices = FRONTENDS, default = STD_FRONTEND, dest = "frontend",
			help = _("the frontend to use - possible values are: %s [default: %%default]") % get_frontend_list())

	parser.add_option("-e", "--ebuild", action = "store", dest = "ebuild",
			help = _("opens the ebuild viewer instead of launching Portato"))

	parser.add_option("--shm", action = "store", nargs = 3, type="long", dest = "shm",
			help = SUPPRESS_HELP)

	parser.add_option("-x", "--validate", action = "store", dest = "validate", metavar="PLUGIN",
			help = _("validates the given plugin xml instead of launching Portato"))

	parser.add_option("-L", "--no-listener", action = "store_true", dest = "nolistener", default = False, 
			help = _("do not start listener"))

	# run parser
	(options, args) = parser.parse_args()

	# evaluate parser's results
	if options.check: # run pychecker
		os.environ['PYCHECKER'] = "--limit 100"
		import pychecker.checker
	
	if len(args): # additional arguments overwrite given frontend
		arg = args[0]
		if arg not in FRONTENDS:
			print _("Unknown frontend '%(frontend)s'. Correct frontends are: %(list)s") % {"frontend": arg, "list": get_frontend_list()}
			sys.exit(2)
		else:
			options.frontend = arg

	try:
		exec ("from portato.gui.%s import run, show_ebuild" % options.frontend)
	except ImportError, e:
		print _("'%(frontend)s' should be installed, but cannot be imported. This is definitly a bug. (%(error)s)") % {"frontend": options.frontend, "error": e[0]}
		sys.exit(1)

	if options.ebuild: # show ebuild
		show_ebuild(options.ebuild)
	elif options.validate: # validate a plugin
		from lxml import etree
		try:
			etree.XMLSchema(file = XSD_LOCATION).assertValid(etree.parse(options.validate))
		except etree.XMLSyntaxError, e:
			print _("Validation failed. XML syntax error: %s.") % e[0]
			sys.exit(3)
		except etree.DocumentInvalid:
			print _("Validation failed. Does not comply with schema.")
			sys.exit(3)
		else:
			print _("Validation succeeded.")
			return

	elif options.nolistener or os.getuid() == 0: # start GUI
		if options.shm:
			get_listener().set_send(*options.shm)
		else:
			get_listener().set_send()
		
		run()
		
	else: # start us again in root modus and launch listener
		
		mem = shm.create_memory(1024, permissions=0600)
		sig = shm.create_semaphore(InitialValue = 0, permissions = 0600)
		rw = shm.create_semaphore(InitialValue = 1, permissions = 0600)
		
		additional = []
		if options.check:
			additional.append("--check")
		if options.frontend:
			additional.extend(["--frontend", options.frontend])

		# set DBUS_SESSION_BUS_ADDRESS to "" to make dbus work as root ;)
		env = os.environ.copy()
		env.update(DBUS_SESSION_BUS_ADDRESS="")
		cmd = SU_COMMAND.split()
		subprocess.Popen(cmd+["%s --no-listener --shm %ld %ld %ld %s" % (sys.argv[0], mem.key, sig.key, rw.key, " ".join(additional))], env = env)
		
		get_listener().set_recv(mem, sig, rw)

if __name__ == "__main__":
	main()
