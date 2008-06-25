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

from .package_22 import PortagePackage_22
from .settings_22 import PortageSettings_22
from .system import PortageSystem

class PortageSystem_22 (PortageSystem):

	def __init__ (self):
		self.settings = PortageSettings_22()
		portage.WORLD_FILE = os.path.join(self.settings.settings["ROOT"],portage.WORLD_FILE)

		self.use_descs = {}
		self.local_use_descs = defaultdict(dict)

		self._version = tuple([x.split("_")[0] for x in portage.VERSION.split(".")])

	def new_package (self, cpv):
		return PortagePackage_22(cpv)
