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
import sys, os
import logging
import gettext
from collections import defaultdict
from threading import Thread, RLock
from functools import wraps

import gtk

# some backend things
from ..backend import flags, system, set_system
from ..helper import debug, info, set_log_level
from ..constants import APP, LOCALE_DIR, USE_SQL, SESSION_DIR

if USE_SQL:
    try:
        import sqlite3 as sql
    except ImportError:
        from pysqlite2 import dbapi2 as sql
    
    import anydbm
    import hashlib

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

        # session configs
        self.session = {}

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

    def set_session (self, name, cat, val):
        self.session[(cat, name)] = val

    def get_session (self, name, cat):
        v = self.session.get((cat, name), None)

        if v == "": v = None
        return v

    def write(self):
        """Writes to the config file and modify any external configs."""
        ConfigParser.write(self)
        self.modify_external_configs()

class DictDatabase (object):
    """An internal database which holds a simple dictionary cat -> [package_list]."""

    ALL = _("ALL")

    def __init__ (self):
        """Constructor."""
        self.__initialize()
        self._lock = RLock()
        self.populate()

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

class SQLDatabase (object):
    
    ALL = _("ALL")
    FORBIDDEN = (".bzr", ".svn", ".git", "CVS", ".hg", "_darcs")

    def __init__ (self):
        """Constructor."""
        self._restrict = ""
        self._lock = RLock()
        
        pkgdb = os.path.join(SESSION_DIR, "package.db")
        pkgdb_existed = os.path.exists(pkgdb)

        if pkgdb_existed:
            debug("package.db already existant")
        else:
            debug("package.db not existant")

        pkg_conn = sql.connect(os.path.join(SESSION_DIR, "package.db"))
        pkg_conn.row_factory = sql.Row
        pkg_conn.execute("""
        CREATE TABLE IF NOT EXISTS packages
        (
            name TEXT,
            cat TEXT,
            inst INTEGER
        )""")

        pkg_conn.commit()
        
        self.was_updated = self.updated()
        if self.was_updated or not pkgdb_existed:
            info(_("Cleaning database..."))
            pkg_conn.execute("DELETE FROM packages") # empty db at beginning
            info(_("Populating database..."))
            self.populate(connection = pkg_conn)
            
        pkg_conn.close()

        descr_conn = sql.connect(os.path.join(SESSION_DIR, "descr.db"))
        descr_conn.execute("""
        CREATE TABLE IF NOT EXISTS descriptions
        (
            cp TEXT,
            descr TEXT
        )""")
        descr_conn.close()

    def updated (self):
        changed = False

        def walk (path):
            debug("Walking %s", path)
            
            for root, dirs, files in os.walk(path):
                for f in files:
                    path = os.path.join(root, f)
                    yield "%s %s" % (f, os.stat(path).st_mtime)
                
                for forbidden in self.FORBIDDEN:
                    if forbidden in dirs:
                        dirs.remove(forbidden)

        overlays = system.get_global_settings("PORTDIR_OVERLAY").split()
        hashes = {}
        for overlay in overlays:
            hashes[overlay] = hashlib.md5("".join(walk(overlay))).hexdigest()
        
        timestamp = os.path.join(system.get_global_settings("PORTDIR"), "metadata/timestamp")
        hashes["ROOT"] = hashlib.md5("%s %s" % (timestamp, os.stat(timestamp).st_mtime)).hexdigest()
    
        dbpath = os.path.join(SESSION_DIR, "portdirs.db")
        db_existed = os.path.exists(dbpath)
        db = anydbm.open(dbpath, "c")
        try:
            if db_existed:
                debug("portdirs.db already existant")
                for key in set(db.keys())- set(hashes.keys()):
                    debug("Overlay '%s' has been removed", key)
                    del db[key]
                    changed = True
                
                for key in hashes.iterkeys():

                    if key not in db.keys():
                        debug("Overlay '%s' has been added.", key)
                        changed = True

                    elif db[key] != hashes[key]:
                        debug("Overlay '%s' has been changed.", key)
                        changed = True
                
                    db[key] = hashes[key]
            else:
                debug("portdirs.db not existant")
                for key in hashes.iterkeys():
                    db[key] = hashes[key]

        finally:
            db.close()

        return changed

    def lock (f):
        @wraps(f)
        def wrapper (self, *args, **kwargs):
            with self._lock:
                r = f(self, *args, **kwargs)
                
            return r
        
        return wrapper

    def con (f):
        @wraps(f)
        def wrapper (*args, **kwargs):
            if not "connection" in kwargs:
                con= sql.connect(os.path.join(SESSION_DIR, "package.db"))
                con.row_factory = sql.Row
                kwargs["connection"] = con

            return f(*args, **kwargs)
        
        return wrapper

    @lock
    @con
    def populate (self, category = None, connection = None):
        """Populates the database.
        
        @param category: An optional category - so only packages of this category are inserted.
        @type category: string
        """

        def _get():
            # get the lists
            inst = system.find_packages(pkgSet = system.SET_INSTALLED, key=category, with_version = False)
            for p in system.find_packages(key = category, with_version = False):
                cat, pkg = p.split("/")

                yield (cat, pkg, p in inst)

        connection.executemany("INSERT INTO packages (cat, name, inst) VALUES (?, ?, ?)", _get())
        connection.commit()

    @lock
    @con
    def get_cat (self, category = None, byName = True, connection = None):
        """Returns the packages in the category.
        
        @param cat: category to return the packages from; if None it defaults to "ALL"
        @type cat: string
        @param byName: selects whether to return the list sorted by name or by installation
        @type byName: boolean
        @return: an iterator over a list of tuples: (category, name, is_installed) or []
        @rtype: L{PkgData}<iterator>
        """

        sort = "ORDER BY name"
        if not byName:
            sort = "ORDER BY inst DESC, name"

        if not category or category == self.ALL:
            c = connection.execute("SELECT cat, name, inst FROM packages WHERE 1=1 %s %s" % (self.restrict, sort))
        else:
            c = connection.execute("SELECT cat, name, inst FROM packages WHERE cat = ? %s %s" % (self.restrict ,sort), (category,))
        
        for pkg in c:
            yield PkgData(pkg["cat"], pkg["name"], pkg["inst"])
        c.close()

    @lock
    @con
    def get_categories (self, installed = False, connection = None):
        """Returns all categories.
        
        @param installed: Only return these with at least one installed package.
        @type installed: boolean
        @returns: the list of categories
        @rtype: string<iterator>
        """

        if installed:
            where = "inst = 1"
        else:
            where = "1 = 1"

        c = connection.execute("SELECT cat FROM packages WHERE %s %s GROUP BY cat" % (where, self.restrict))

        l = c.fetchall()
        c.close()

        if len(l) > 1:
            yield self.ALL
        
        for cat in l:
            yield cat["cat"]

    @lock
    @con
    def reload (self, cat = None, connection = None):
        """Reloads the given category.
        
        @param cat: category
        @type cat: string
        """

        if cat:
            connection.execute("DELETE FROM packages WHERE cat = ?", (cat,))
            connection.commit()
            self.populate(cat+"/", connection = connection)
        else:
            connection.execute("DELETE FROM packages")
            connection.commit()
            self.populate(connection = connection)

    def get_restrict (self):
        return self._restrict

    @lock
    def set_restrict (self, restrict):
        if not restrict:
            self._restrict = ""
        else:
            self._restrict = "AND name LIKE '%%%s%%'" % restrict

    restrict = property(get_restrict, set_restrict)

if USE_SQL:
    Database = SQLDatabase
else:
    Database = DictDatabase
