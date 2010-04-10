# -*- coding: utf-8 -*-
#
# File: portato/backend/portage/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from future_builtins import map, filter, zip

from ...helper import debug
from portage import VERSION as PV

VERSION = tuple(map(int, (x.split("_")[0] for x in PV.split("."))))

if VERSION >= (2, 2):
    debug("Using portage-2.2")
    from .system_22 import PortageSystem_22 as PortageSystem
    from .package_22 import PortagePackage_22 as PortagePackage
else:
    debug("Using portage-2.1")
    from .system import PortageSystem
    from .package import PortagePackage
