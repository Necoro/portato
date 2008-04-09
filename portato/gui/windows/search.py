# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/search.py
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

class SearchWindow (AbstractDialog):
	"""A window showing the results of a search process."""
	
	def __init__ (self, parent, list, jump_to):
		"""Constructor.

		@param parent: parent-window
		@type parent: gtk.Window
		@param list: list of results to show
		@type list: string[]
		@param jump_to: function to call if "OK"-Button is hit
		@type jump_to: function(string)"""
		
		AbstractDialog.__init__(self, parent)
		
		self.jump_to = jump_to # function to call for jumping
		self.list = list
		self.list.sort()
		
		# combo box
		self.searchList = self.tree.get_widget("searchList")
		self.build_sort_list()
		self.searchList.get_selection().select_path(0)

		# finished --> show
		self.window.show_all()

	def build_sort_list (self):
		"""Builds the sort list."""
		
		store = gtk.ListStore(str)
		self.searchList.set_model(store)

		# build categories
		for p in self.list:
			store.append(["%s/<b>%s</b>" % tuple(p.split("/"))])

		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn(_("Results"), cell, markup = 0)
		self.searchList.append_column(col)

	def ok (self, *args):
		self.jump()
		self.close()
	
	def jump (self, *args):
		model, iter = self.searchList.get_selection().get_selected()
		self.jump_to(self.list[model.get_path(iter)[0]])

	def cb_key_pressed_combo (self, widget, event):
		"""Emulates a ok-button-click."""
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == "Return": # take it as an "OK" if Enter is pressed
			self.jump()
			return True
		else:
			return False
