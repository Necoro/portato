#!/usr/bin/python
# -*- coding: utf-8 -*-

from distutils.core import setup, Extension
from portato.constants import VERSION, DATA_DIR, FRONTENDS

packages = ["portato", "portato.gui", "portato.backend", "portato.backend.portage"]
ext_modules = []
data_files = []
cmdclass = {}

if "gtk" in FRONTENDS:
	packages.append("portato.gui.gtk")
	data_files.append((DATA_DIR, ["portato/gui/gtk/glade/portato.glade"]))

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
