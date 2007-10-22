#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# File: setup.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import sys, os, os.path
from distutils.core import setup, Extension
from portato.constants import FRONTENDS, VERSION, DATA_DIR, ICON_DIR, PLUGIN_DIR, TEMPLATE_DIR

### copied from shm's setup.py ###
MacrosAndDefines = [ ]

# HAVE_UNION_SEMUN needs to be #defined on FreeBSD and OS X and must *not* be #defined
# on Linux. On other systems, I'm not sure. Please let me know if you find that you
# need to make changes for your platform.
if ("bsd" in sys.platform) or ("darwin" in sys.platform):
    MacrosAndDefines.append( ('HAVE_UNION_SEMUN', None) )
### end copy ###

def plugin_list (*args):
	"""Creates a list of correct plugin pathes out of the arguments."""
	return [("plugins/%s.xml" % x) for x in args]

def ui_file_list ():
	"""Returns the list of *.ui-files."""
	uis = [x for x in os.listdir("portato/gui/templates/ui/") if x.endswith(".ui")]
	return [os.path.join("portato/gui/templates/ui",x) for x in uis]

packages = ["portato", "portato.gui", "portato.plugins", "portato.backend", "portato.backend.portage", "portato.backend.catapult", "portato.shm"]
ext_modules = [Extension("portato.shm.shm", ["shm/shmmodule.c"], define_macros = MacrosAndDefines, extra_compile_args=["-fPIC"])]
data_files = [(ICON_DIR, ["icons/portato-icon.png"]), (PLUGIN_DIR, plugin_list("shutdown", "resume_loop")), (DATA_DIR, ["plugin.xsd", "ebuild.lang"])]
cmdclass = {}
package_dir = {"portato.shm" : "shm"}

if "gtk" in FRONTENDS:
	packages.append("portato.gui.gtk")
	data_files.append((DATA_DIR, ["portato/gui/templates/portato.glade"]))

if "qt" in FRONTENDS:
	packages.append("portato.gui.qt")
	data_files.append((os.path.join(DATA_DIR,"ui"), ui_file_list()))

# do the distutils setup
setup(name="Portato",
		version = VERSION,
		description = "Frontends to Portage",
		license = "GPLv2",
		url = "http://portato.origo.ethz.ch/",
		author = "René 'Necoro' Neumann",
		author_email = "necoro@necoro.net",
		packages = packages,
		data_files = data_files,
		ext_modules = ext_modules,
		cmdclass = cmdclass,
		package_dir = package_dir
		)
