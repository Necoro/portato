#!/usr/bin/python
# -*- coding: utf-8 -*-

from distutils.core import setup, Extension
from geneticone.constants import VERSION, DATA_DIR

setup(name="Genetic/One",
		version=VERSION,
		author="René 'Necoro' Neumann",
		license="GPLv2",
		author_email="necoro@necoro.net",
		packages=["geneticone", "geneticone.gui", "geneticone.backend", "geneticone.gui.gtk"],
		data_files={DATA_DIR: ["geneticone/gui/gtk/glade/geneticone.glade"]}
		)
