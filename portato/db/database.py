# -*- coding: utf-8 -*-
#
# File: portato/db/database.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

class PkgData (object):
    __slots__ = ("cat", "pkg", "inst")

    def __init__ (self, cat, pkg, inst):
        self.cat = cat
        self.pkg = pkg
        self.inst = inst

    def __iter__ (self):
        return iter((self.cat, self.pkg, self.inst))

    def __cmp__ (self, other):
        return cmp(self.pkg.lower(), other.pkg.lower())

    def __repr__ (self):
        return "<Package (%(cat)s, %(pkg)s, %(inst)s)>" % {"cat" : self.cat, "pkg" : self.pkg, "inst" : self.inst}

class Database (object):

    def populate (self, category = None):
        raise NotImplentedError

    def get_cat (self, cat = None, byName = True):
        raise NotImplentedError

    def get_categories (self, installed = False):
        raise NotImplentedError

    def reload (self, cat = None):
        raise NotImplentedError
