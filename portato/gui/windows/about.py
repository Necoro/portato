# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/about.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import gtk

from .basic import AbstractDialog
from ...constants import VERSION

class AboutWindow (AbstractDialog):
    """A window showing the "about"-informations."""

    def __init__ (self, parent):

        AbstractDialog.__init__(self, parent)

        self.window.set_version(VERSION)
        self.window.set_logo(None)

        self.window.show_all()

