# -*- coding: utf-8 -*-
#
# File: portato/db/hash.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import re
from collections import defaultdict

from ..helper import info
from ..backend import system
from .database import Database, PkgData

class HashDatabase (Database):
    """An internal database which holds a simple dictionary cat -> [package_list]."""

    lock = Database.lock

    def __init__ (self, session):
        """Constructor."""
        Database.__init__(self)
        self.session = session

        self.__initialize()
        self.populate()

    def __initialize (self):
        self._db = defaultdict(list)
        self.inst_cats = set([self.ALL])
        self._restrict = None

    def __sort_key (self, x):
        return x.pkg.lower()

    @lock
    def populate (self, category = None):
        
        # get the lists
        packages = system.find_packages(category, with_version = False)
        installed = system.find_packages(category, system.SET_INSTALLED, with_version = False)
        
        # cycle through packages
        for p in packages:
            cat, pkg = p.split("/")
            inst = p in installed
            t = PkgData(cat, pkg, inst, False)
            self._db[cat].append(t)
            self._db[self.ALL].append(t)

            if inst:
                self.inst_cats.add(cat)

        for key in self._db: # sort alphabetically
            self._db[key].sort(key = self.__sort_key)

    @lock
    def get_cat (self, cat = None, byName = True, showDisabled = False):
        if not cat:
            cat = self.ALL

        def get_pkgs():
            if byName:
                for pkg in self._db[cat]:
                    if showDisabled or not pkg.disabled:
                        yield pkg
            else:
                ninst = []
                for pkg in self._db[cat]:
                    if not showDisabled and pkg.disabled: continue

                    if pkg.inst:
                        yield pkg
                    else:
                        ninst.append(pkg)

                for pkg in ninst:
                    yield pkg

        try:
            if self.restrict:
                return (pkg for pkg in get_pkgs() if self.restrict.search(pkg.cat+"/"+pkg.pkg))
            else:
                return get_pkgs()

        except KeyError: # cat is in category list - but not in portage
            info(_("Catched KeyError => %s seems not to be an available category. Have you played with rsync-excludes?"), cat)

    @lock
    def get_categories (self, installed = False):
        if not self.restrict:
            if installed:
                cats = self.inst_cats
            else:
                cats = self._db.iterkeys()

        else:
            if installed:
                cats = set((pkg.cat for pkg in self.get_cat(self.ALL) if pkg.inst))
            else:
                cats = set((pkg.cat for pkg in self.get_cat(self.ALL)))

            if len(cats)>1:
                cats.add(self.ALL)

        return (cat for cat in cats)

    @lock
    def reload (self, cat = None):
        if cat:
            del self._db[cat]
            try:
                self.inst_cats.remove(cat)
            except KeyError: # not in inst_cats - can be ignored
                pass
            
            self._db[self.ALL] = filter(lambda x: x.cat != cat, self._db[self.ALL])
            self.populate(cat+"/*")
        else:
            self.__initialize()
            self.populate()

    @lock
    def disable (self, cpv):
        cat, pkg = cpv.split("/")

        c = self._db[cat]
        p = c[c.index(PkgData(cat, pkg))]
        p.disabled = True

    def get_restrict (self):
        return self._restrict

    @lock
    def set_restrict (self, restrict):
        if not restrict:
            self._restrict = None
        else:
            try:
                regex = re.compile(restrict, re.I)
            except re.error, e:
                info(_("Error while compiling search expression: '%s'."), str(e))
            else: # only set self._restrict if no error occurred
                self._restrict = regex

    restrict = property(get_restrict, set_restrict)
