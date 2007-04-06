#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, os.path
from distutils.core import setup, Extension
from portato.constants import VERSION, DATA_DIR, FRONTENDS

packages = ["portato", "portato.gui", "portato.plugins", "portato.backend", "portato.backend.portage"]
ext_modules = []
data_files = []
cmdclass = {}

if "gtk" in FRONTENDS:
	packages.append("portato.gui.gtk")
	data_files.append((DATA_DIR, ["portato/gui/gtk/glade/portato.glade"]))

if "qt" in FRONTENDS:
	packages.append("portato.gui.qt")
	data_files.append((os.path.join(DATA_DIR,"ui"), [os.path.join("portato/gui/qt/ui",x) for x in os.listdir("portato/gui/qt/ui/") if x.endswith(".ui")]))

setup(name="Portato",
		version = VERSION,
		author = "René 'Necoro' Neumann",
		license = "GPLv2",
		author_email = "necoro@necoro.net",
		packages = packages,
		data_files = data_files,
		ext_modules = ext_modules,
		cmdclass = cmdclass
		)
