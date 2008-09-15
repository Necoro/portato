# -*- coding: utf-8 -*-
#
# File: portato/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from . import log

# start logging
log.start(file=False)

# listener-handling
__listener = None

def get_listener():
    global __listener
    if __listener is None:
        from .plistener import PListener
        __listener = PListener()
    
    return __listener
