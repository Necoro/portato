# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/plugin.py
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
from ...backend import system
from ...helper import debug

class PluginWindow (AbstractDialog):
	
	statsStore = gtk.ListStore(str)
	
	for s in (_("Disabled"), _("Temporarily enabled"), _("Enabled"), _("Temporarily disabled")):
		statsStore.append([s])

	def __init__ (self, parent, plugins):
		"""Constructor.

		@param parent: the parent window
		@type parent: gtk.Window"""
		
		AbstractDialog.__init__(self, parent)
		self.plugins = plugins
		self.changedPlugins = {}

		self.buttons = map(self.tree.get_widget, ("disabledRB", "tempEnabledRB", "enabledRB", "tempDisabledRB"))
		map(lambda b: b.set_mode(False), self.buttons)

		self.descrLabel = self.tree.get_widget("descrLabel")
		self.authorLabel = self.tree.get_widget("authorLabel")

		self.depExpander = self.tree.get_widget("depExpander")
		self.installBtn = self.tree.get_widget("installBtn")
		self.depList = self.tree.get_widget("depList")
		self.build_dep_list()

		self.instIcon = self.window.render_icon(gtk.STOCK_YES, gtk.ICON_SIZE_MENU)
		
		self.view = self.tree.get_widget("pluginList")
		self.store = gtk.ListStore(str)
		
		self.view.set_model(self.store)
		
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Plugin", cell, markup = 0)
		self.view.append_column(col)
		
		for p in plugins:
			self.store.append(["<b>%s</b>" % p.name])

		self.view.get_selection().connect("changed", self.cb_list_selection)

		self.window.show_all()

	def build_dep_list (self):
		store = gtk.ListStore(gtk.gdk.Pixbuf, str)

		self.depList.set_model(store)

		col = gtk.TreeViewColumn()

		cell = gtk.CellRendererPixbuf()
		col.pack_start(cell, False)
		col.add_attribute(cell, "pixbuf", 0)

		cell = gtk.CellRendererText()
		col.pack_start(cell, True)
		col.add_attribute(cell, "text", 1)

		self.depList.append_column(col)

	def fill_dep_list (self, inst = [], ninst = []):
		store = self.depList.get_model()
		store.clear()

		for dep in inst:
			store.append([self.instIcon, dep])
		for dep in ninst:
			store.append([None, dep])

	def cb_state_toggled (self, rb):
	
		plugin = self.get_actual()

		if plugin:
			state = self.buttons.index(rb)

			self.changedPlugins[plugin] = state
			debug("new changed plugins: %s => %d", plugin.name, state)

	def cb_ok_clicked (self, btn):
		for plugin, val in self.changedPlugins.iteritems():
			plugin.status = val

		self.close()
		return True

	def cb_list_selection (self, selection):
		plugin = self.get_actual()
		
		if plugin:
			if not plugin.description:
				self.descrLabel.hide()
			else:
				self.descrLabel.set_markup(plugin.description)
				self.descrLabel.show()

			self.authorLabel.set_label(plugin.author)
			
			status = self.changedPlugins.get(plugin, plugin.status)
			self.buttons[status].set_active(True)

			if plugin.deps:
				inst = []
				ninst = []

				for dep in plugin.deps:
					if system.find_packages(dep, pkgSet = "installed"):
						inst.append(dep)
					else:
						ninst.append(dep)

				self.fill_dep_list(inst, ninst)
				self.depExpander.show()
				
				self.installBtn.show()
				self.installBtn.set_sensitive(bool(ninst))
			else:
				self.installBtn.hide()
				self.depExpander.hide()

	def get_actual (self):
		store, it = self.view.get_selection().get_selected()

		if it:
			return self.plugins[int(store.get_path(it)[0])]
		else:
			return None
