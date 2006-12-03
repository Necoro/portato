# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/wrapper.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from portato.gui.wrapper import Tree, Console

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
		self.emergeIt = self.append(None, ["Emerge", ""])
		self.unmergeIt = self.append(None, ["Unmerge", ""])

	def build_append_value (self, cpv, oneshot = False, update = False, version = None):
		string = ""

		if oneshot:
			string += "<i>oneshot</i>"
			if update: string += "; "

		if update:
			string += "<i>updating</i>"
			if version != None:
				string += "<i> from version %s</i>" % version

		return [cpv, string]

	def get_emerge_it (self):
		return self.emergeIt

	def get_unmerge_it (self):
		return self.unmergeIt

	def is_in_emerge (self, it):
		return self.get_path_from_iter(it).split(":")[0] == self.get_path_from_iter(self.emergeIt)

	def is_in_unmerge (self, it):
		return self.get_path_from_iter(it).split(":")[0] == self.get_path_from_iter(self.unmergeIt)
	
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

	def get_path_from_iter (self, it):
		return self.tree.get_string_from_iter(it)

	def append (self, parent = None, values = None):
		return self.tree.append(parent, values)

	def remove (self, it):
		return self.tree.remove(it)

	def get_original (self):
		return self.tree

	def get_cpv_column (self):
		return self.cpv_col

class GtkConsole (Console):
	"""The implementation of the abstract Console for GTK."""

	def __init__ (self, console):
		"""Constructor.

		@param console: the original console
		@type console: vte.Terminal"""
		
		self.console = console

	def get_window_title(self):
		return self.console.get_window_title()

	def set_pty (self, pty):
		self.console.set_pty(pty)

	def get_original (self):
		return self.console
