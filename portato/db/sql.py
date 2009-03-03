# -*- coding: utf-8 -*-
#
# File: portato/db/sql.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
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

try:
    import cPickle as pickle
except ImportError:
    import pickle

import hashlib
import os

from functools import wraps

from ..constants import SESSION_DIR
from ..helper import info, error, debug
from ..backend import system
from .database import Database, PkgData

class SQLDatabase (Database):
    
    FORMAT = "1"
    FORBIDDEN = (".bzr", ".svn", ".git", "CVS", ".hg", "_darcs")
    lock = Database.lock

    def __init__ (self, session):
        """Constructor."""
        Database.__init__(self)

        self._restrict = ""
        self.session = session
        
        updateFormat = False
        if "format" not in session or session["format"] != self.FORMAT:
            session["format"] = self.FORMAT
            updateFormat = True

        pkgdb = os.path.join(SESSION_DIR, "package.db")
        pkgdb_existed = os.path.exists(pkgdb)

        if pkgdb_existed:
            debug("package.db already existant")
        else:
            debug("package.db not existant")

        pkg_conn = sql.connect(os.path.join(SESSION_DIR, "package.db"))
        pkg_conn.row_factory = sql.Row
        if pkgdb_existed and updateFormat:
            pkg_conn.execute("DROP TABLE packages")

        pkg_conn.execute("""
        CREATE TABLE IF NOT EXISTS packages
        (
            name TEXT,
            cat TEXT,
            inst INTEGER,
            disabled INTEGER
        )""")

        pkg_conn.commit()
        
        self.was_updated = self.updated()
        if self.was_updated or not pkgdb_existed or updateFormat:
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

        if db_existed and "pickle" not in self.session:
            debug("Removing old portdirs.db, as this looks like old DBM format. If it is not - well - no real harm ;)")
            os.remove(dbpath)
            db_existed = False

        self.session["pickle"] = True # no need for a certain value

        if db_existed:
            debug("portdirs.db already existant")
            with open(dbpath, "rb") as dbfile:
                db = pickle.load(dbfile)

            # the following could be simplified - losing the debug possibilities
            # so we keep it as is :)
            # there shouldn't be so much overlays, that this would result
            # in performance loss

            for key in set(db.keys()) - set(hashes.keys()):
                debug("Overlay '%s' has been removed", key)
                changed = True
            
            for key in hashes.iterkeys():

                if key not in db:
                    debug("Overlay '%s' has been added.", key)
                    changed = True

                elif db[key] != hashes[key]:
                    debug("Overlay '%s' has been changed.", key)
                    changed = True
            
        else:
            debug("portdirs.db not existant")
            changed = True
        
        if changed:
            with open(dbpath, "wb") as dbfile:
                db = pickle.dump(hashes, dbfile, protocol = -1)

        return changed

    def con (f):
        @wraps(f)
        def wrapper (*args, **kwargs):
            if not "connection" in kwargs:
                con= sql.connect(os.path.join(SESSION_DIR, "package.db"))
                con.row_factory = sql.Row
                kwargs["connection"] = con

            return f(*args, **kwargs)
        
        return Database.lock(wrapper)

    @con
    def populate (self, category = None, connection = None):
        def _get():
            # get the lists
            inst = system.find_packages(pkgSet = system.SET_INSTALLED, key=category, with_version = False)
            for p in system.find_packages(key = category, with_version = False):
                cat, pkg = p.split("/")

                yield (cat, pkg, p in inst, False)

        connection.executemany("INSERT INTO packages (cat, name, inst, disabled) VALUES (?, ?, ?, ?)", _get())
        connection.commit()

    @con
    def get_cat (self, category = None, byName = True, showDisabled = False, connection = None):
        sort = "ORDER BY name"
        if not byName:
            sort = "ORDER BY inst DESC, name"

        disabled = "1=1"
        if not showDisabled:
            disabled = "disabled = 0"

        if not category or category == self.ALL:
            c = connection.execute("SELECT cat, name, inst, disabled FROM packages WHERE %s %s %s" % (disabled, self.restrict, sort))
        else:
            c = connection.execute("SELECT cat, name, inst, disabled FROM packages WHERE cat = ? AND %s %s %s" % (disabled, self.restrict ,sort), (category,))
        
        for pkg in c:
            yield PkgData(pkg["cat"], pkg["name"], pkg["inst"], pkg["disabled"])
        c.close()

    @con
    def get_categories (self, installed = False, connection = None):

        if installed:
            where = "inst = 1"
        else:
            where = "1 = 1"

        c = connection.execute("SELECT cat FROM packages WHERE disabled = 0 AND %s %s GROUP BY cat" % (where, self.restrict))

        l = c.fetchall()
        c.close()

        if len(l) > 1:
            yield self.ALL
        
        for cat in l:
            yield cat["cat"]

    @con
    def reload (self, cat = None, connection = None):
        if cat:
            connection.execute("DELETE FROM packages WHERE cat = ?", (cat,))
            connection.commit()
            self.populate(cat+"/*", connection = connection)
        else:
            connection.execute("DELETE FROM packages")
            connection.commit()
            self.populate(connection = connection)

    @con
    def disable (self, cpv, connection = None):
        cat, pkg = cpv.split("/")
        connection.execute("UPDATE packages SET disabled = 1 WHERE cat = ? AND name = ?", (cat, pkg))
        connection.commit()

    def get_restrict (self):
        return self._restrict

    @lock
    def set_restrict (self, restrict):
        if not restrict:
            self._restrict = ""
        else:
            restrict = restrict.replace(".*","%").replace(".","_")
            
            if "/" in restrict:
                cat,pkg = restrict.split("/")
                self._restrict = "AND name LIKE '%s%%' AND cat LIKE '%s'" % (pkg, cat)
            else:
                self._restrict = "AND (name LIKE '%%%(restrict)s%%' OR cat LIKE '%(restrict)s%%')" % {"restrict":restrict}

    restrict = property(get_restrict, set_restrict)
