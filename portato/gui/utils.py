# -*- coding: utf-8 -*-
#
# File: portato/gui/utils.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

# some stuff needed
import re
import sys
import logging
import gettext
from collections import defaultdict
from threading import Thread, RLock
from functools import wraps

import gtk

# some backend things
from ..backend import flags, system, set_system
from ..helper import debug, info, set_log_level
from ..constants import APP, LOCALE_DIR

# parser
from ..config_parser import ConfigParser

def get_color (cfg, name):
    return gtk.gdk.color_parse("#%s" % cfg.get(name, section = "COLORS"))

class GtkThread (Thread):
    def run(self):
        # for some reason, I have to install this for each thread ...
        gettext.install(APP, LOCALE_DIR, unicode = True)
        try:
            Thread.run(self)
        except SystemExit:
            raise # let normal thread handle it
        except:
            type, val, tb = sys.exc_info()
            try:
                sys.excepthook(type, val, tb, thread = self.getName())
            except TypeError:
                raise type, val, tb # let normal thread handle it
            finally:
                del type, val, tb

class Config (ConfigParser):
    
    def __init__ (self, cfgFile):
        """Constructor.

        @param cfgFile: path to config file
        @type cfgFile: string"""

        ConfigParser.__init__(self, cfgFile)
        
        # read config
        self.parse()

        # local configs
        self.local = {}

    def modify_flags_config (self):
        """Sets the internal config of the L{flags}-module.
        @see: L{flags.set_config()}"""

        flagCfg = {
                "usefile": self.get("useFile"),
                "usePerVersion" : self.get_boolean("usePerVersion"),
                "maskfile" : self.get("maskFile"),
                "maskPerVersion" : self.get_boolean("maskPerVersion"),
                "testingfile" : self.get("keywordFile"),
                "testingPerVersion" : self.get_boolean("keywordPerVersion")}
        flags.set_config(flagCfg)

    def modify_debug_config (self):
        if self.get_boolean("debug"):
            level = logging.DEBUG
        else:
            level = logging.INFO

        set_log_level(level)

    def modify_system_config (self):
        """Sets the system config.
        @see: L{backend.set_system()}"""
        set_system(self.get("system"))

    def modify_external_configs (self):
        """Convenience function setting all external configs."""
        self.modify_debug_config()
        self.modify_flags_config()
        self.modify_system_config()

    def set_local(self, cpv, name, val):
        """Sets some local config.

        @param cpv: the cpv describing the package for which to set this option
        @type cpv: string (cpv)
        @param name: the option's name
        @type name: string
        @param val: the value to set
        @type val: any"""
        
        if not cpv in self.local:
            self.local[cpv] = {}

        self.local[cpv].update({name:val})

    def get_local(self, cpv, name):
        """Returns something out of the local config.

        @param cpv: the cpv describing the package from which to get this option
        @type cpv: string (cpv)
        @param name: the option's name
        @type name: string
        @return: value stored for the cpv and name or None if not found
        @rtype: any"""

        if not cpv in self.local:
            return None
        if not name in self.local[cpv]:
            return None

        return self.local[cpv][name]

    def write(self):
        """Writes to the config file and modify any external configs."""
        ConfigParser.write(self)
        self.modify_external_configs()

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
    """An internal database which holds a simple dictionary cat -> [package_list]."""

    ALL = _("ALL")

    def __init__ (self):
        """Constructor."""
        self.__initialize()
        self._lock = RLock()

    def lock (f):
        @wraps(f)
        def wrapper (self, *args, **kwargs):
            with self._lock:
                r = f(self, *args, **kwargs)
            return r
        
        return wrapper

    def __initialize (self):
        self._db = defaultdict(list)
        self.inst_cats = set([self.ALL])
        self._restrict = None

    def __sort_key (self, x):
        return x.pkg.lower()

    @lock
    def populate (self, category = None):
        """Populates the database.
        
        @param category: An optional category - so only packages of this category are inserted.
        @type category: string
        """
        
        # get the lists
        packages = system.find_packages(category, with_version = False)
        installed = system.find_packages(category, system.SET_INSTALLED, with_version = False)
        
        # cycle through packages
        for p in packages:
            cat, pkg = p.split("/")
            inst = p in installed
            t = PkgData(cat, pkg, inst)
            self._db[cat].append(t)
            self._db[self.ALL].append(t)

            if inst:
                self.inst_cats.add(cat)

        for key in self._db: # sort alphabetically
            self._db[key].sort(key = self.__sort_key)

    @lock
    def get_cat (self, cat = None, byName = True):
        """Returns the packages in the category.
        
        @param cat: category to return the packages from; if None it defaults to "ALL"
        @type cat: string
        @param byName: selects whether to return the list sorted by name or by installation
        @type byName: boolean
        @return: an iterator over a list of tuples: (category, name, is_installed) or []
        @rtype: (string, string, boolean)<iterator>
        """
        
        if not cat:
            cat = self.ALL

        def get_pkgs():
            if byName:
                for pkg in self._db[cat]:
                    yield pkg
            else:
                ninst = []
                for pkg in self._db[cat]:
                    if pkg.inst:
                        yield pkg
                    else:
                        ninst.append(pkg)

                for pkg in ninst:
                    yield pkg

        try:
            if self.restrict:
                return (pkg for pkg in get_pkgs() if self.restrict.search(pkg.pkg))#if pkg[1].find(self.restrict) != -1)
            else:
                return get_pkgs()

        except KeyError: # cat is in category list - but not in portage
            info(_("Catched KeyError => %s seems not to be an available category. Have you played with rsync-excludes?"), cat)

    @lock
    def get_categories (self, installed = False):
        """Returns all categories.
        
        @param installed: Only return these with at least one installed package.
        @type installed: boolean
        @returns: the list of categories
        @rtype: string<iterator>
        """

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
        """Reloads the given category.
        
        @param cat: category
        @type cat: string
        """

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
