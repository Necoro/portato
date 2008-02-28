# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/basic.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

# gtk stuff
import gtk
import gtk.glade
import gobject

from functools import wraps
import os.path

from ...constants import TEMPLATE_DIR, APP_ICON, APP, LOCALE_DIR

gtk.glade.bindtextdomain (APP, LOCALE_DIR)
gtk.glade.textdomain (APP)
GLADE_FILE = TEMPLATE_DIR+"portato.glade"

class Window (object):
	def __init__ (self):

		if not hasattr(self, "__tree__"):
			self.__tree__ = self.__class__.__name__

		if not hasattr(self, "__window__"):
			self.__window__ = self.__class__.__name__

		if not hasattr(self, "__file__"):
			self.__file__ = self.__class__.__name__

		self.tree = self.get_tree(self.__tree__)
		self.tree.signal_autoconnect(self)
		self.window = self.tree.get_widget(self.__window__)
		self.window.set_icon_from_file(APP_ICON)

	@staticmethod
	def watch_cursor (func):
		"""This is a decorator for functions being so time consuming, that it is appropriate to show the watch-cursor.
		@attention: this function relies on the gtk.Window-Object being stored as self.window"""
		
		@wraps(func)
		def wrapper (self, *args, **kwargs):
			ret = None
			def cb_idle():
				try:
					ret = func(self, *args, **kwargs)
				finally:
					self.window.window.set_cursor(None)
				return False
			
			watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
			self.window.window.set_cursor(watch)
			gobject.idle_add(cb_idle)
			return ret

		return wrapper

	def get_tree (self, name):
		return gtk.glade.XML(os.path.join(TEMPLATE_DIR, self.__file__+".glade"), name)

class AbstractDialog (Window):
	"""A class all our dialogs get derived from. It sets useful default vars and automatically handles the ESC-Button."""

	def __init__ (self, parent):
		"""Constructor.

		@param parent: the parent window
		@type parent: gtk.Window"""
		
		Window.__init__(self)

		# set parent
		self.window.set_transient_for(parent)
		self.parent = parent
		
		# catch the ESC-key
		self.window.connect("key-press-event", self.cb_key_pressed)

	def cb_key_pressed (self, widget, event):
		"""Closes the window if ESC is pressed."""
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == "Escape":
			self.close()
			return True
		else:
			return False

	def close (self, *args):
		self.window.destroy()

class Popup (object):

	def __init__ (self, name, parent, file = "popups"):
		self.tree = gtk.glade.XML(os.path.join(TEMPLATE_DIR, file+".glade"), root = name)
		self.tree.signal_autoconnect(parent)
		self._popup = self.tree.get_widget(name)

	def popup (self, *args):
		self._popup.popup(*args)
