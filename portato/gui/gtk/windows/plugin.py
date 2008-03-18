# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/windows/plugin.py
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
from ....helper import debug, _

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

		view = self.tree.get_widget("pluginList")
		self.store = gtk.ListStore(str,str,str)
		
		view.set_model(self.store)
		
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn(_("Plugin"), cell, markup = 0)
		view.append_column(col)
		
		col = gtk.TreeViewColumn(_("Authors"), cell, text = 1)
		view.append_column(col)

		ccell = gtk.CellRendererCombo()
		ccell.set_property("model", self.statsStore)
		ccell.set_property("text-column", 0)
		ccell.set_property("has-entry", False)
		ccell.set_property("editable", True)
		ccell.connect("edited", self.cb_status_changed)
		col = gtk.TreeViewColumn(_("Status"), ccell, markup = 2)
		view.append_column(col)
		
		for p in (("<b>"+p.name+"</b>", p.author, _(self.statsStore[p.status][0])) for p in plugins):
			self.store.append(p)

		self.window.show_all()

	def cb_status_changed (self, cell, path, new_text):
		path = int(path)
		
		self.store[path][2] = "<b>%s</b>" % new_text

		# convert string to constant
		const = None
		for num, val in enumerate(self.statsStore):
			if val[0] == new_text:
				const = num
				break

		assert (const is not None)

		self.changedPlugins.update({self.plugins[path] : const})
		debug("new changed plugins: %s => %d", self.plugins[path].name, const)

	def cb_ok_clicked (self, btn):
		for plugin, val in self.changedPlugins.iteritems():
			plugin.status = val

		self.close()
		return True
