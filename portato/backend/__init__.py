# -*- coding: utf-8 -*-
#
# File: portato/backend/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import sys, copy, os
from threading import Lock

# import portage
import portage

class PortageSettings:
	"""Encapsulation of the portage settings.
	
	@ivar settings: portage settings
	@ivar settingslock: a simple Lock
	@ivar trees: a dictionary of the trees
	@ivar porttree: shortcut to C{trees[root]["porttree"]}
	@ivar vartree: shortcut to C{trees[root]["vartree"]}
	@ivar virtuals: shortcut to C{trees[root]["virtuals"]}"""

	def __init__ (self):
		"""Initializes the instance. Calls L{load()}."""
		self.settingslock = Lock()
		self.load()
		
	def load(self):
		"""(Re)loads the portage settings and sets the variables."""

		kwargs = {}
		for k, envvar in (("config_root", "PORTAGE_CONFIGROOT"), ("target_root", "ROOT")):
			kwargs[k] = os.environ.get(envvar, None)
		self.trees = portage.create_trees(trees=None, **kwargs)

		self.settings = self.trees["/"]["vartree"].settings

		for myroot in self.trees:
			if myroot != "/":
				self.settings = self.trees[myroot]["vartree"].settings
				break

		self.settings.unlock()

		root = self.settings["ROOT"]

		self.porttree = self.trees[root]["porttree"]
		self.vartree  = self.trees[root]["vartree"]
		self.virtuals = self.trees[root]["virtuals"]
		
		portage.settings = None # we use our own one ...

# portage tree vars
portage_settings = PortageSettings()

# for the moment ;)
settingslock = portage_settings.settingslock
settings = portage_settings.settings
trees = portage_settings.trees
porttree = portage_settings.porttree
vartree = portage_settings.vartree
virtuals = portage_settings.virtuals

# this is set to "var/lib/portage/world" by default - so we add the leading /
portage.WORLD_FILE = portage_settings.settings["ROOT"]+portage.WORLD_FILE

# import our packages
from exceptions import *
from package import *
from portage_helper import *
