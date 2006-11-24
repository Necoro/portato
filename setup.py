#!/usr/bin/python
# -*- coding: utf-8 -*-

from distutils.core import setup, Extension
from portato.constants import VERSION, DATA_DIR

setup(name="Portato",
		version=VERSION,
		author="René 'Necoro' Neumann",
		license="GPLv2",
		author_email="necoro@necoro.net",
		packages=["portato", "portato.gui", "portato.backend", "portato.gui.gtk"],
		data_files=[(DATA_DIR, ["portato/gui/gtk/glade/portato.glade"])]
		)
