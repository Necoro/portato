#
# File: geneticone/backend/__init__.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import sys

# insert the gentoolkit-location into syspath
sys.path.insert(0, "/usr/lib/gentoolkit/pym")

# import gentoolkit and portage
import gentoolkit
import portage

# this is set to "var/lib/portage/world" by default - so we add the leading /
portage.WORLD_FILE = portage.settings["ROOT"]+portage.WORLD_FILE
portage.settings = None # we use our own one ...

# portage tree vars
porttree = gentoolkit.porttree
vartree = gentoolkit.vartree

# import our packages
from exceptions import *
from package import *
from portage_helper import *
