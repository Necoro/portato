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

from PyQt4 import QtGui, QtCore
from portato.gui.wrapper import Tree
 
class QtTree (Tree):

	def __init__ (self, treeWidget, col = 0):

		self.tree = treeWidget
		self.col = col
		
		self.emergeIt = QtGui.QTreeWidgetItem(self.tree, ["Emerge", ""])
		self.unmergeIt = QtGui.QTreeWidgetItem(self.tree, ["Unmerge", ""])

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
		iter = QtGui.QTreeWidgetItemIterator(it)
		iter += 1 # next iter ...
		return iter.value()

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

		return QtGui.QTreeWidgetItem(parent, values)

	def remove (self, it):
		# a somehow strange approach ;) - go to the parent and delete the child
		parent = it.parent()
		index = parent.indexOfChild(it)
		parent.takeChild(index)

	def get_original (self):
		return self.tree

	def get_cpv_column (self):
		return self.col

