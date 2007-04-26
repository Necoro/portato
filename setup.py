#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, os.path
from distutils.core import setup, Extension
from portato.constants import VERSION, DATA_DIR, FRONTENDS, ICON_DIR

packages = ["portato", "portato.gui", "portato.plugins", "portato.backend", "portato.backend.portage", "portato.extern"]
ext_modules = []
data_files = [(ICON_DIR, ["icons/portato-icon.png"])]
cmdclass = {}

if "gtk" in FRONTENDS:
	packages.append("portato.gui.gtk")
	data_files.append((DATA_DIR, ["portato/gui/templates/portato.glade"]))

if "qt" in FRONTENDS:
	packages.append("portato.gui.qt")
	data_files.append((os.path.join(DATA_DIR,"ui"), [os.path.join("portato/gui/templates/ui",x) for x in os.listdir("portato/gui/templates/ui/") if x.endswith(".ui")]))

setup(name="Portato",
		version = VERSION,
		description = "Frontends to Portage",
		license = "GPLv2",
		url = "http://portato.sourceforge.net/",
		author = "René 'Necoro' Neumann",
		author_email = "necoro@necoro.net",
		packages = packages,
		data_files = data_files,
		ext_modules = ext_modules,
		cmdclass = cmdclass
		)
