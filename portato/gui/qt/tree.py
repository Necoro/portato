# -*- coding: utf-8 -*-
#
# File: portato/gui/qt/tree.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from PyQt4 import Qt
from portato.gui.wrapper import Tree
 
from portato.helper import debug
from portato.backend import system # for the tooltips

class QtTree (Tree):

	def __init__ (self, treeWidget, col = 0):

		self.tree = treeWidget
		self.col = col
		
		self.emergeIt = Qt.QTreeWidgetItem(self.tree, ["Emerge", ""])
		self.unmergeIt = Qt.QTreeWidgetItem(self.tree, ["Unmerge", ""])

	def build_append_value (self, cpv, oneshot = False, update = False, version = None):
		string = ""

		if oneshot:
			string += "(oneshot)"
			if update: string += "; "

		if update:
			string += "(updating"
			if version is not None:
				string += " from version %s" % version
			string += ")"

		return [cpv, string]

	def get_emerge_it (self):
		return self.emergeIt

	def get_unmerge_it (self):
		return self.unmergeIt

	def is_in_emerge (self, it):
		while self.iter_has_parent(it):
			it = self.parent_iter(it)
		return (it == self.emergeIt)

	def is_in_unmerge (self, it):
		return not self.is_in_emerge(it)

	def iter_has_parent (self, it):
		return (it.parent() != None)

	def parent_iter (self, it):
		return it.parent()

	def first_child_iter (self, it):
		return it.child(0)

	def iter_has_children (self, it):
		return (it.childCount() > 0)

	def next_iter (self, it):
		iter = Qt.QTreeWidgetItemIterator(it)
		iter += 1 # next iter ...
		
		newIt = iter.value()
		if not newIt or newIt.parent() != it.parent(): # stop if we left the current parent
			return None
		else:
			return newIt

	def get_value (self, it, column):
		return str(it.text(column))

	def append (self, parent = None, values = None):
		if values is None:
			values = ["",""]
		else:
			for i in range(len(values)):
				if values[i] is None:
					values[i] = ""

		if parent is None:
			parent = self.tree
		
		item = Qt.QTreeWidgetItem(parent, values)
		self.make_tooltip(item)
		return item

	def remove (self, it):
		# a somehow strange approach ;) - go to the parent and delete the child
		parent = it.parent()
		index = parent.indexOfChild(it)
		parent.takeChild(index)

	def get_original (self):
		return self.tree

	def get_cpv_column (self):
		return self.col
	
	def make_tooltip (self, item):
		tooltip = self.__get_flags(str(item.text(0)))
		item.setToolTip(self.col, tooltip)

	def __get_flags(self, cpv):
		
		try:
			pkg = system.new_package(cpv)
		except ValueError: # no CPV
			return ""

		enabled = []
		disabled = []
		expanded = set()

		pkg_flags = pkg.get_all_use_flags()
		if not pkg_flags: # no flags - stop here
			return ""
		
		pkg_flags.sort()
		for use in pkg_flags:
			exp = pkg.use_expanded(use)
			if exp:
				expanded.add(exp)
			
			else:
				if pkg.is_use_flag_enabled(use):
					enabled.append(use)
				else:
					disabled.append(use)
		
		string = ""
		
		if enabled:
			string = "<b>+%s</b>" % ("<br>+".join(enabled),)
			if len(disabled) > 0:
				string = string + "<br>"
		
		if disabled:
			string = string+"<i>- %s</i>" % ("<br>- ".join(disabled),)

		if expanded:
			string = string+"<br><br>"+"<br>".join(expanded)

		return string

