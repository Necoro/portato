#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# File: setup.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import sys, os, os.path
from distutils.core import setup, Extension
from portato.constants import VERSION, DATA_DIR, ICON_DIR, PLUGIN_DIR, TEMPLATE_DIR

def plugin_list (*args):
	"""Creates a list of correct plugin pathes out of the arguments."""
	return [("plugins/%s.xml" % x) for x in args]

packages = ["portato", "portato.gui", "portato.gui.windows", "portato.plugins", "portato.backend", "portato.backend.portage"]
data_files = [
		(TEMPLATE_DIR, [os.path.join("portato/gui/templates",x) for x in os.listdir("portato/gui/templates") if x.endswith(".glade")]),
		(ICON_DIR, ["icons/portato-icon.png"]),
		(PLUGIN_DIR, plugin_list("dbus_init")), 
		(DATA_DIR, ["plugin.xsd"])]

# do the distutils setup
setup(name="Portato",
		version = VERSION,
		description = "GTK-Frontend to Portage",
		license = "GPLv2",
		url = "http://portato.origo.ethz.ch/",
		author = "René 'Necoro' Neumann",
		author_email = "necoro@necoro.net",
		packages = packages,
		data_files = data_files
		)
