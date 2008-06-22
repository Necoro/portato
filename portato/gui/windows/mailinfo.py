# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/mailinfo.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import gtk

from .basic import AbstractDialog
from ...helper import debug

class MailInfoWindow (AbstractDialog):

	def __init__ (self, parent, tb):

		AbstractDialog.__init__(self, parent)
		self.window.show_all()

	def cb_cancel_clicked (self):

		self.close()
		return True
