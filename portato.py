#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# File: portato.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import with_statement, absolute_import

import sys, os, subprocess
import gettext, locale
from optparse import OptionParser, SUPPRESS_HELP

from portato import get_listener
from portato.constants import VERSION, XSD_LOCATION, LOCALE_DIR, APP, SU_COMMAND

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
	
	parser.add_option("--shm", action = "store", nargs = 3, type="long", dest = "shm",
			help = SUPPRESS_HELP)

	parser.add_option("-x", "--validate", action = "store", dest = "validate", metavar="PLUGIN",
			help = _("validates the given plugin xml instead of launching Portato"))

	parser.add_option("-F", "--no-fork", "-L", action = "store_true", dest = "nofork", default = False, 
			help = _("do not fork off as root") + (" (%s)" % _("-L is deprecated")))

	# run parser
	(options, args) = parser.parse_args()

	if options.validate: # validate a plugin
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
	
	elif options.nofork or os.getuid() == 0: # start GUI
		from portato.gui import run
		
		if options.shm:
			get_listener().set_send(*options.shm)
		else:
			get_listener().set_send()
		
		run()
		
	else: # start us again in root modus and launch listener
		
		try:
			import shm_wrapper as shm
		except ImportError:
			from portato._shm import shm_wrapper as shm

		mem = shm.create_memory(1024, permissions=0600)
		sig = shm.create_semaphore(InitialValue = 0, permissions = 0600)
		rw = shm.create_semaphore(InitialValue = 1, permissions = 0600)
		
		# set DBUS_SESSION_BUS_ADDRESS to "" to make dbus work as root ;)
		env = os.environ.copy()
		env.update(DBUS_SESSION_BUS_ADDRESS="")
		cmd = SU_COMMAND.split()
		subprocess.Popen(cmd+["%s --no-fork --shm %ld %ld %ld" % (sys.argv[0], mem.key, sig.key, rw.key)], env = env)
		
		get_listener().set_recv(mem, sig, rw)

if __name__ == "__main__":
	main()
