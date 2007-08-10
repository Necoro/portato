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

# gtk stuff
import gtk
import gtk.glade
import gobject

from portato.constants import DATA_DIR, APP_ICON, APP, LOCALE_DIR

gtk.glade.bindtextdomain (APP, LOCALE_DIR)
gtk.glade.textdomain (APP)
GLADE_FILE = DATA_DIR+"portato.glade"

class Window (object):
	def __init__ (self):
		self.tree = self.get_tree(self.__class__.__name__)
		self.tree.signal_autoconnect(self)
		self.window = self.tree.get_widget(self.__class__.__name__)
		self.window.set_icon_from_file(APP_ICON)

	@staticmethod
	def watch_cursor (func):
		"""This is a decorator for functions being so time consuming, that it is appropriate to show the watch-cursor.
		@attention: this function relies on the gtk.Window-Object being stored as self.window"""
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

		wrapper.__dict__ = func.__dict__
		wrapper.__name__ = func.__name__
		wrapper.__doc__ = func.__doc__
		return wrapper

	def get_tree (self, name):
		return gtk.glade.XML(GLADE_FILE, name)

class AbstractDialog (Window):
	"""A class all our dialogs get derived from. It sets useful default vars and automatically handles the ESC-Button."""

	def __init__ (self, parent):
		"""Constructor.

		@param parent: the parent window
		@type parent: gtk.Window"""
		
		Window.__init__(self)

		# set parent
		self.window.set_transient_for(parent)
		
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

	def __init__ (self, name, parent):
		self.tree = gtk.glade.XML(GLADE_FILE, root = name)
		self.tree.signal_autoconnect(parent)
		self._popup = self.tree.get_widget(name)

	def popup (self, *args):
		self._popup.popup(*args)
