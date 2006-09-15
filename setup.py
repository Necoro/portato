#!/usr/bin/python

from distutils.core import setup, Extension

thread = Extension("geneticone.modules.geneticthread", sources=["geneticone/modules/geneticthread.c"])

setup(name="Genetic/One",
		version="0.1-alpha",
		author="Necoro d.M. et.al.",
		author_email="geneticone@projects.necoro.net",
		packages=["geneticone", "geneticone.gui", "genetic.modules"],
		ext_modules=[thread]
		)
