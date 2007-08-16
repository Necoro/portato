# -*- coding: utf-8 -*-
#
# File: portato/gui/wrapper.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

class Tree:
	"""This represents an abstract of a Tree-Widget. It should be used for all operations not in a specific frontend, where a Tree is needed.
	Each frontend _MUST_ define its own subclass and implement ALL of the methods, otherwise a NotImplementedError will be thrown."""

	def iter_has_parent (self, it):
		"""Returns whether the actual iterator has a parent.

		@param it: the iterator
		@type it: Iterator
		@returns: True if it has a parent it, else False.
		@rtype: boolean"""
		raise NotImplementedError

	def parent_iter (self, it):
		"""Returns the parent iter.

		@param it: the iterator
		@type it: Iterator
		@returns: Parent iterator or None if the current it has no parent.
		@rtype: Iterator; None"""
		raise NotImplementedError 
	
	def first_child_iter (self, it):
		"""Returns the first child iter.

		@param it: the iterator
		@type it: Iterator
		@returns: First child iterator or None if the current it has no children.
		@rtype: Iterator; None"""
		raise NotImplementedError

	def iter_has_children (self, it):
		"""Returns whether the actual iterator has children.

		@param it: the iterator
		@type it: Iterator
		@returns: True if it has children, else False.
		@rtype: boolean"""
		raise NotImplementedError

	def next_iter (self, it):
		"""Returns the next iter.

		@param it: the iterator
		@type it: Iterator
		@returns: Next iterator or None if the current iter is the last one.
		@rtype: Iterator; None"""
		raise NotImplementedError

	def get_value (self, it, column):
		"""Returns the value of the specific column at the given iterator.

		@param it: the iterator
		@type it: Iterator
		@param column: the column of the iterator from where to get the value
		@type column: int
		@returns: the value
		@rtype: anything"""
		raise NotImplementedError

	def append (self, parent = None, values = None):
		"""Appends some values right after the given parent. If parent is None, it is appended as the first element.

		@param parent: the iterator to append the values right after; if None it symbolizes the top
		@type parent: Iterator
		@param values: a list of values which are going to be appended to the tree
		@type values: list
		@returns: Iterator pointing to the newly appended stuff
		@rtype: Iterator"""
		raise NotImplementedError

	def remove(self, it):
		"""Removes an iterator out of the tree. 
		@attention: The iterator can point to anything hereafter. Do not reuse!
		
		@param it: iterator to remove
		@type it: Iterator"""
		raise NotImplementedError

	def get_original(self):
		"""Returns the original tree-object.
		
		@returns: original tree-object
		@rtype: tree-object"""
		raise NotImplementedError
	
	#
	# the "design" part
	#

	def get_cpv_column (self):
		"""Returns the number of the column where the cpv's are stored.

		@returns: column with cpv's
		@rtype: int"""
		raise NotImplementedError

	def is_in_emerge (self, it):
		"""Checks whether an iterator is part of the "Emerge" section.

		@param it: the iterator to check
		@type it: Iterator
		@returns: True if the iter is part; False otherwise
		@rtype: boolean"""
		raise NotImplementedError

	def is_in_unmerge (self, it):
		"""Checks whether an iterator is part of the "Unmerge" section.

		@param it: the iterator to check
		@type it: Iterator
		@returns: True if the iter is part; False otherwise
		@rtype: boolean"""
		raise NotImplementedError

	def get_emerge_it (self):
		"""Returns an iterator signaling the top of the emerge section.

		@returns: emerge-iterator
		@rtype: Iterator"""
		raise NotImplementedError

	def get_unmerge_it (self):
		"""Returns an iterator signaling the top of the unmerge section.

		@returns: unmerge-iterator
		@rtype: Iterator"""
		raise NotImplementedError

	def build_append_value (self, cpv, oneshot = False, update = False, downgrade = False, version = None, useChange = []):
		"""Builds the list, which is going to be passed to append. 

		@param cpv: the cpv
		@type cpv: string (cpv)
		@param oneshot: True if oneshot
		@type oneshot: boolean
		@param update: True if this is an update
		@type update: boolean
		@param downgrade: True if this is a downgrade
		@type downgrade: boolean
		@param version: the version we update from
		@type version: string
		@param useChange: list of changed useflags; use "-use" for removed and "+use" for added flags
		@type useChange: string[]

		@returns: the created list
		@rtype: list"""
		raise NotImplementedError

class Console:
	"""This represents the abstract of a console. It should be used for all operations not in a specific frontend, where a console is needed.
	Each frontend _MUST_ define its own subclass and implement ALL of the methods, otherwise a NotImplementedError will be thrown."""
	
	def set_pty (self, pty):
		"""This sets the pseudo-terminal where to print the incoming output to.

		@param pty: the terminal to print to
		@type pty: file-descriptor"""
		raise NotImplementedError

	def get_window_title (self):
		"""This should return the current title of the console. If this is not possible, it must return None.

		@returns: title of the console or None"""
		raise NotImplementedError
