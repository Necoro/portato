# -*- coding: utf-8 -*-
#
# File: portato/backend/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import sys, copy
from threading import Lock

# import portage
import portage

# portage tree vars
settingslock = Lock()
settings = portage.config(clone=portage.settings, config_incrementals = copy.deepcopy(portage.settings.incrementals))
porttree = portage.db[portage.root]["porttree"]
vartree  = portage.db[portage.root]["vartree"]
virtuals = portage.db[portage.root]["virtuals"]
trees = portage.db

# this is set to "var/lib/portage/world" by default - so we add the leading /
portage.WORLD_FILE = portage.settings["ROOT"]+portage.WORLD_FILE
portage.settings = None # we use our own one ...

# import our packages
from exceptions import *
from package import *
from portage_helper import *
