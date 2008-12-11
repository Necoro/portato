# -*- coding: utf-8 -*-
#
# File: portato/backend/portage/system_22.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import os
import portage

from collections import defaultdict

from .package_22 import PortagePackage_22
from .settings_22 import PortageSettings_22
from .system import PortageSystem
from . import sets as syssets

class PortageSystem_22 (PortageSystem):

    def __init__ (self):
        self.settings = PortageSettings_22()
        portage.WORLD_FILE = os.path.join(self.settings.global_settings["ROOT"],portage.WORLD_FILE)

        self.use_descs = {}
        self.local_use_descs = defaultdict(dict)

        self.setmap = {
                self.SET_ALL : syssets.AllSet,
                self.SET_INSTALLED : syssets.InstalledSet,
                self.SET_UNINSTALLED : syssets.UninstalledSet,
                self.SET_TREE : syssets.TreeSet
                }

    def get_update_option (self):
        return ["--update", "--oneshot"] # --oneshot to not record the used sets in world file

    def has_set_support (self):
        return True

    def get_sets (self, description = False):
        if description:
            return ((name, set.description) for name, set in self.settings.setsconfig.getSets().iteritems())
        else:
            return tuple(self.settings.setsconfig.getSets())

    def _get_set (self, pkgSet):
        pkgSet = pkgSet.lower()
        if pkgSet == "": pkgSet = self.SET_ALL

        s = self.setmap.get(pkgSet, None)
        if s is None:
            return syssets.PortageSet(pkgSet)
        else:
            return s()

    def new_package (self, cpv):
        return PortagePackage_22(cpv)
