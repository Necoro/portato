#!/usr/bin/python

from distutils.core import setup, Extension

#thread = Extension("geneticone.modules.geneticthread", sources=["geneticone/modules/geneticthread.c"])

setup(name="Genetic/One",
		version="SVN",
		author="René 'Necoro' Neumann",
		license="GPLv2",
		author_email="necoro@necoro.net",
		packages=["geneticone", "geneticone.gui", "geneticone.backend"],
		#ext_modules=[thread]
		)
