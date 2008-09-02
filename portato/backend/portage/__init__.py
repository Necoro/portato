# -*- coding: utf-8 -*-
#
# File: portato/backend/portage/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from portage import VERSION as PV

VERSION = tuple(map(int, (x.split("_")[0] for x in PV.split("."))))

if VERSION >= (2, 2):
    from .system_22 import PortageSystem_22 as PortageSystem
    from .package_22 import PortagePackage_22 as PortagePackage
else:
    from .system import PortageSystem
    from .package import PortagePackage
