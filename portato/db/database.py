# -*- coding: utf-8 -*-
#
# File: portato/db/database.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

from threading import RLock
from functools import wraps
from ..helper import error

class UnsupportedSearchTypeError(Exception):
    pass

class PkgData (object):
    __slots__ = ("cat", "pkg", "inst", "disabled")

    def __init__ (self, cat, pkg, inst = False, disabled = False):
        self.cat = cat
        self.pkg = pkg
        self.inst = inst
        self.disabled = disabled

    def __iter__ (self):
        return iter((self.cat, self.pkg, self.inst, self.disabled))

    def __cmp__ (self, other):
        return cmp(self.pkg.lower(), other.pkg.lower())

    def __repr__ (self):
        return "<Package (%(cat)s, %(pkg)s, %(inst)s)>" % {"cat" : self.cat, "pkg" : self.pkg, "inst" : self.inst}

class Database (object):

    ALL = _("ALL")

    SEARCH_NAME = 1
    SEARCH_DESCRIPTION = 2

    TYPES = {
            SEARCH_NAME = _("Name"),
            SEARCH_DESCRIPTION = _("Description"),
            SEARCH_NAME | SEARCH_DESCRIPTION = _("Name + Description")
            }


    def __init__ (self):
        self._lock = RLock()
        self.type = self.SEARCH_NAME

    @staticmethod
    def lock (f):
        @wraps(f)
        def wrapper (self, *args, **kwargs):
            with self._lock:
                r = f(self, *args, **kwargs)
                
            return r
        
        return wrapper

    def search_types (self):
        """The types of search supported by the database.

        @return: type
        @rtype: int"""
        raise NotImplentedError

    def set_type (self, type):
        if type & self.search_types() == 0:
            error("Search type %s not supported by database '%s'.", type, self.__class__.__name__)
            raise UnsupportedSearchTypeError, type

        self._type = type

    def get_type (self):
        return self._type

    type = property(get_type, set_type)

    def populate (self, category = None):
        """Populates the database.
        
        @param category: An optional category - so only packages of this category are inserted.
        @type category: string
        """
        raise NotImplentedError

    def get_cat (self, cat = None, byName = True, showDisabled = False):
        """Returns the packages in the category.
        
        @param cat: category to return the packages from; if None it defaults to C{ALL}
        @type cat: string
        @param byName: selects whether to return the list sorted by name or by installation
        @type byName: boolean
        @param showDisabled: should disabled packages be returned
        @type showDisabled: boolean
        @return: an iterator over the packages
        @rtype: L{PkgData}<iterator>
        """
        raise NotImplentedError

    def get_categories (self, installed = False):
        """Returns all categories.
        
        @param installed: Only return these with at least one installed package.
        @type installed: boolean
        @returns: the list of categories
        @rtype: string<iterator>
        """
        raise NotImplentedError

    def disable (self, cpv):
        """Marks the CPV as disabled.

        @param cpv: the cpv to mark
        """
        raise NotImplentedError

    def reload (self, cat = None):
        """Reloads the given category.
        
        @param cat: category
        @type cat: string
        """
        raise NotImplentedError
