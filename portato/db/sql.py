# -*- coding: utf-8 -*-
#
# File: portato/db/sql.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

try:
    import sqlite3 as sql
except ImportError:
    from pysqlite2 import dbapi2 as sql

import anydbm
import hashlib
import os

from functools import wraps
from threading import RLock

from ..helper import info, error, debug
from ..backend import system
from .database import Database, PkgData

class SQLDatabase (Database):
    
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
