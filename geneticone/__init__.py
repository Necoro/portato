#!/usr/bin/python
import sys

# insert the gentoolkit-location into syspath
sys.path.insert(0, "/usr/lib/gentoolkit/pym")

# import gentoolkit and portage
import gentoolkit
import portage

# this is set to "var/lib/portage/world" by default - so we add the leading /
portage.WORLD_FILE = "/"+portage.WORLD_FILE

# portage tree vars
porttree = gentoolkit.porttree
vartree = gentoolkit.vartree

# import our packages
from helper import *
from package import *
import modules
