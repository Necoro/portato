# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/splash.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import gtk
import gobject
from gettext import lgettext as _

from ...constants import VERSION, APP_ICON
from .basic import Window

class SplashScreen (Window):
	
	def __init__ (self, startStr = ""):
		Window.__init__(self)

		self.image = self.tree.get_widget("image")
		self.genLabel = self.tree.get_widget("generalLabel")
		self.descrLabel = self.tree.get_widget("descrLabel")
		
		self.image.set_from_file(APP_ICON)
		self.genLabel.set_label("<b><big>Portato %s ...</big></b>" % VERSION)
		
		self.set_descr(startStr)

	def set_descr (self, string):
		self.descrLabel.set_label(_("... is starting up: %s") % string)
		self.do_iteration()

	def do_iteration (self):
		while gtk.events_pending():
			gtk.main_iteration()
	
	def show (self):
		self.window.show_all()
		self.do_iteration()

	def hide (self):
		self.window.hide()
		self.do_iteration()

	__call__ = set_descr
