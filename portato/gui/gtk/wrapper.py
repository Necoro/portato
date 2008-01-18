# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/wrapper.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import vte
from gettext import lgettext as _
from ..wrapper import Tree, Console
from ...helper import debug

class GtkTree (Tree):
	"""The implementation of the abstract tree."""

	def __init__ (self, tree, col = 0):
		"""Constructor.

		@param tree: original tree
		@type tree: gtk.TreeStore
		@param col: the column where the cpv is stored
		@type col: int"""

		self.tree = tree
		self.cpv_col = col
		self.emergeIt = None
		self.unmergeIt = None
		self.updateIt = None

	def build_append_value (self, cpv, oneshot = False, update = False, downgrade = False, version = None, useChange = []):
		string = ""

		if oneshot:
			string += "<i>%s</i>" % _("oneshot")

		if update:
			if oneshot: string += "; "
			if version is not None:
				string += "<i>%s</i>" % (_("updating from version %s") % version)
			else:
				string += "<i>%s</i>" % _("updating")

		elif downgrade:
			if oneshot: string += "; "
			if version is not None:
				string += "<i>%s</i>" % (_("downgrading from version %s") % version)
			else:
				string += "<i>%s</i>" % _("downgrading")

		if useChange:
			if update or downgrade or oneshot: string += "; "
			string += "<i><b>%s </b></i>" % _("IUSE changes:")
			useChange.sort()
			string += "<i>%s</i>" % " ".join(useChange)

		return [cpv, string]

	def set_in_progress (self, it):
		iter = self.tree.get_iter_from_string(self.tree.get_string_from_iter(it).split(":")[0])
		self.tree.set_value(iter, 1, "<b>%s</b>" % _("(In Progress)"))

	def get_emerge_it (self):
		if self.emergeIt is None:
			self.emergeIt = self.append(None, ["<b>%s</b>" % _("Install"), ""])
		return self.emergeIt

	def get_unmerge_it (self):
		if self.unmergeIt is None:
			self.unmergeIt = self.append(None, ["<b>%s</b>" % _("Uninstall"), ""])

		return self.unmergeIt

	def get_update_it (self):
		if self.updateIt is None:
			self.updateIt = self.append(None, ["<b>%s</b>" % _("Update"), ""])

		return self.updateIt

	def is_in (self, it, in_it):
		return in_it and self.tree.get_string_from_iter(it).split(":")[0] == self.tree.get_string_from_iter(in_it)

	def is_in_emerge (self, it):
		return self.is_in(it, self.emergeIt)

	def is_in_unmerge (self, it):
		return self.is_in(it, self.unmergeIt)

	def is_in_update (self, it):
		return self.is_in(it, self.updateIt)
	
	def iter_has_parent (self, it):
		return (self.tree.iter_parent(it) != None)

	def parent_iter (self, it):
		return self.tree.iter_parent(it)

	def first_child_iter (self, it):
		return self.tree.iter_children(it)

	def iter_has_children (self, it):
		return self.tree.iter_has_child(it)

	def next_iter (self, it):
		return self.tree.iter_next(it)

	def get_value (self, it, column):
		return self.tree.get_value(it, column)

	def iter_equal (self, it, other_it):
		return self.tree.get_string_from_iter(it) == self.tree.get_string_from_iter(other_it)

	def append (self, parent = None, values = None):
		return self.tree.append(parent, values)

	def remove (self, it):
		
		if self.emergeIt and self.iter_equal(it, self.emergeIt) : self.emergeIt = None
		elif self.unmergeIt and self.iter_equal(it, self.unmergeIt) : self.unmergeIt = None
		elif self.updateIt and self.iter_equal(it, self.updateIt) : self.updateIt = None
		
		self.tree.remove(it)

	def get_original (self):
		return self.tree

	def get_cpv_column (self):
		return self.cpv_col

class GtkConsole (vte.Terminal, Console):
	"""The implementation of the abstract Console for GTK."""
	
	def reset (self):
		vte.Terminal.reset(self, True, True)
