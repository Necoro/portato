# -*- coding: utf-8 -*-
#
# File: portato/gui/wrapper.py
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
from ..helper import debug

class GtkTree (object):
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
        """
        Builds the list, which is going to be passed to append. 

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
        @rtype: list
        """

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

        return [cpv, string, False]

    def set_in_progress (self, it, to = True):
        """
        Marks the queue where the given iterator belongs as being in progress.

        @param it: one iterator of the queue to mark to
        @type it: Iterator
        @param to: whether to enable or disable
        @type to: boolean
        """

        iter = self.first_iter(it)
        if to:
            self.tree.set_value(iter, 1, "<b>%s</b>" % _("(In Progress)"))
        else:
            self.tree.set_value(iter, 1, "")
        
        self.tree.set_value(iter, 2, to)

    def is_in_progress (self, it):
        """
        Returns whether the queue where the given iterator belongs to, is marked as "being in progress".

        @param it: the iterator
        @type it: Iterator
        @returns: whether the queue is marked "in progress"
        @rtype: boolean
        """
        return self.tree.get_value(it, 2)

    def get_emerge_it (self):
        """
        Returns an iterator signaling the top of the emerge section.

        @returns: emerge-iterator
        @rtype: Iterator
        """
        if self.emergeIt is None:
            self.emergeIt = self.append(None, ["<b>%s</b>" % _("Install"), "", False])
        return self.emergeIt

    def get_unmerge_it (self):
        """
        Returns an iterator signaling the top of the unmerge section.

        @returns: unmerge-iterator
        @rtype: Iterator
        """
        if self.unmergeIt is None:
            self.unmergeIt = self.append(None, ["<b>%s</b>" % _("Uninstall"), "", False])

        return self.unmergeIt

    def get_update_it (self):
        """
        Returns an iterator signaling the top of the update section.

        @returns: unmerge-iterator
        @rtype: Iterator
        """
        if self.updateIt is None:
            self.updateIt = self.append(None, ["<b>%s</b>" % _("Update"), "", False])

        return self.updateIt

    def first_iter (self, it):
        """
        Returns the iterator at the top.

        @param it: the iterator
        @type it: Iterator
        @returns: the top iterator
        @rtype: Iterator
        """
        return self.tree.get_iter_from_string(self.tree.get_string_from_iter(it).split(":")[0])

    def is_in (self, it, in_it):
        return in_it and self.iter_equal(self.first_iter(it), in_it)

    def is_in_emerge (self, it):
        """
        Checks whether an iterator is part of the "Emerge" section.

        @param it: the iterator to check
        @type it: Iterator
        @returns: True if the iter is part; False otherwise
        @rtype: boolean
        """
        return self.is_in(it, self.emergeIt)

    def is_in_unmerge (self, it):
        """
        Checks whether an iterator is part of the "Unmerge" section.

        @param it: the iterator to check
        @type it: Iterator
        @returns: True if the iter is part; False otherwise
        @rtype: boolean
        """
        return self.is_in(it, self.unmergeIt)

    def is_in_update (self, it):
        """
        Checks whether an iterator is part of the "Update" section.

        @param it: the iterator to check
        @type it: Iterator
        @returns: True if the iter is part; False otherwise
        @rtype: boolean
        """
        return self.is_in(it, self.updateIt)
    
    def iter_has_parent (self, it):
        """
        Returns whether the actual iterator has a parent.
        @param it: the iterator
        @type it: Iterator
        @returns: True if it has a parent it, else False.
        @rtype: boolean
        """
        return (self.tree.iter_parent(it) != None)

    def parent_iter (self, it):
        """
        Returns the parent iter.

        @param it: the iterator
        @type it: Iterator
        @returns: Parent iterator or None if the current it has no parent.
        @rtype: Iterator; None
        """
        return self.tree.iter_parent(it)

    def first_child_iter (self, it):
        """
        Returns the first child iter.

        @param it: the iterator
        @type it: Iterator
        @returns: First child iterator or None if the current it has no children.
        @rtype: Iterator; None
        """

        return self.tree.iter_children(it)

    def iter_has_children (self, it):
        """
        Returns whether the actual iterator has children.

        @param it: the iterator
        @type it: Iterator
        @returns: True if it has children, else False.
        @rtype: boolean
        """

        return self.tree.iter_has_child(it)

    def next_iter (self, it):
        """
        Returns the next iter.

        @param it: the iterator
        @type it: Iterator
        @returns: Next iterator or None if the current iter is the last one.
        @rtype: Iterator; None
        """
        return self.tree.iter_next(it)

    def get_value (self, it, column):
        """
        Returns the value of the specific column at the given iterator.

        @param it: the iterator
        @type it: Iterator
        @param column: the column of the iterator from where to get the value
        @type column: int
        @returns: the value
        @rtype: anything
        """

        return self.tree.get_value(it, column)

    def iter_equal (self, it, other_it):
        """
        Checks whether to iterators are equal.

        @param it: the one iterator to compare
        @type it: Iterator
        @param other_it: the other iterator to compare
        @type other_it: Iterator
        @returns: True if both iterators are equal; False otherwise
        @rtype boolean
        """
        return self.tree.get_string_from_iter(it) == self.tree.get_string_from_iter(other_it)

    def append (self, parent = None, values = None):
        """
        Appends some values right after the given parent. If parent is None, it is appended as the first element.

        @param parent: the iterator to append the values right after; if None it symbolizes the top
        @type parent: Iterator
        @param values: a list of values which are going to be appended to the tree
        @type values: list
        @returns: Iterator pointing to the newly appended stuff
        @rtype: Iterator
        """

        return self.tree.append(parent, values)

    def remove (self, it):
        """
        Removes an iterator out of the tree. 
        @attention: The iterator can point to anything hereafter. Do not reuse!
        
        @param it: iterator to remove
        @type it: Iterator
        """
        
        if self.emergeIt and self.iter_equal(it, self.emergeIt) : self.emergeIt = None
        elif self.unmergeIt and self.iter_equal(it, self.unmergeIt) : self.unmergeIt = None
        elif self.updateIt and self.iter_equal(it, self.updateIt) : self.updateIt = None
        
        self.tree.remove(it)

    def get_original (self):
        """
        Returns the original tree-object.
        
        @returns: original tree-object
        @rtype: tree-object
        """
        return self.tree

    def get_cpv_column (self):
        """
        Returns the number of the column where the cpv's are stored.

        @returns: column with cpv's
        @rtype: int
        """
        return self.cpv_col

class GtkConsole (vte.Terminal):
    """The implementation of the abstract Console for GTK."""
    
    def reset (self):
        """
        Resets the terminal.
        """
        vte.Terminal.reset(self, True, True)
