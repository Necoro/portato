# -*- coding: utf-8 -*-
#
# File: portato/backend/portage/settings.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import os
import portage
from threading import Lock

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
        self.trees = None
        self.load()
        
    def load(self):
        """(Re)loads the portage settings and sets the variables."""

        kwargs = {}
        for k, envvar in (("config_root", "PORTAGE_CONFIGROOT"), ("target_root", "ROOT")):
            kwargs[k] = os.environ.get(envvar, None)
        self.trees = portage.create_trees(trees=self.trees, **kwargs)

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
        self.global_settings = portage.config(clone=self.settings)
        self._cpv = None
        
        portage.settings = None # we use our own one ...

    def setcpv (self, cpv, **kwargs):
        if cpv != self._cpv:
            self.settings.setcpv(cpv, **kwargs)
            self._cpv = cpv

    def reset (self):
        self.settings.reset()
        self._cpv = None
