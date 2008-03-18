# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/update.py
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
from ..dialogs import unmask_dialog, blocked_dialog
from ...backend import system
from ...backend.exceptions import PackageNotFoundException, BlockedException
from ...helper import _, debug

class UpdateWindow (AbstractDialog):

	def __init__ (self, parent, packages, queue, jump_to):
		AbstractDialog.__init__(self, parent)

		self.queue = queue
		self.jump = jump_to

		self.packages = system.sort_package_list(packages)

		self.build_list()

		self.window.show_all()

	def build_list (self):

		store = gtk.ListStore(bool, str)
		self.view = self.tree.get_widget("packageList")
		self.view.set_model(store)

		cell = gtk.CellRendererText()
		tCell = gtk.CellRendererToggle()
		tCell.set_property("activatable", True)
		tCell.connect("toggled", self.cb_check_toggled) # emulate the normal toggle behavior ...
		
		self.view.append_column(gtk.TreeViewColumn(_("Enabled"), tCell, active = 0))
		self.view.append_column(gtk.TreeViewColumn(_("Package"), cell, text = 1))

		for p in self.packages:
			store.append([False, p.get_cpv()])

	def cb_set_size (self, *args):
		"""
		This callback is called shortly before drawing.
		It calculates the optimal size of the window.
		The optimum is defined as: as large as possible w/o scrollbars
		"""

		bb = self.tree.get_widget("updateBB")
		vals = (self.view.get_vadjustment().upper+bb.size_request()[1]+10, # max size of list + size of BB + constant
				self.parent.get_size()[1]) # size of the parent -> maximum size
		debug("Size values for the list and for the parent: %d / %d", *vals)
		val = int(min(vals))
		debug("Minimum value: %d", val)
		self.window.set_geometry_hints(self.window, min_height = val)

	def cb_select_all_clicked (self, btn):
		model = self.view.get_model()
		iter = model.get_iter_first()
		
		while iter:
			model.set_value(iter, 0, True)
			iter = model.iter_next(iter)

		return True

	def cb_install_clicked (self, btn):
		model = self.view.get_model()
		iter = model.get_iter_first()
		if iter is None: return

		items = []
		while iter:
			if model.get_value(iter, 0):
				items.append(model.get_value(iter, 1))
			iter = model.iter_next(iter)
		
		for item in items:
			try:
				try:
					self.queue.append(item, type = "install", oneshot = True)
				except PackageNotFoundException, e:
					if unmask_dialog(e[0]) == gtk.RESPONSE_YES :
						self.queue.append(item, type = "install", unmask = True, oneshot = True)

			except BlockedException, e:
				blocked_dialog(e[0], e[1])

		self.close()
		return True

	def cb_package_selected (self, view):
		sel = view.get_selection()
		store, it = sel.get_selected()
		if it:
			package = system.new_package(store.get_value(it, 1))

			self.jump(package.get_cp(), package.get_version())

		return True

	def cb_check_toggled (self, cell, path):
		# for whatever reason we have to define normal toggle behavior explicitly
		store = self.view.get_model()
		store[path][0] = not store[path][0]
		return True
