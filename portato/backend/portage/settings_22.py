# -*- coding: utf-8 -*-
#
# File: portato/backend/portage/settings_22.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

try:
    import portage.sets as psets
except ImportError:
    import portage._sets as psets

from .settings import PortageSettings

class PortageSettings_22 (PortageSettings):
    """Enhances the normal PortageSettings in ways, that it adds the setsconfig."""

    def __init__ (self):
        PortageSettings.__init__(self)

    def load (self):
        PortageSettings.load(self)

        self.setsconfig = psets.load_default_config(self.settings, self.trees[self.settings["ROOT"]])
