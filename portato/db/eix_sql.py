# -*- coding: utf-8 -*-
#
# File: portato/db/eix_sql.py
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

import os

from .sql import SQLDatabase
from ..eix import EixReader
from ..helper import debug
from ..backend import system

class EixSQLDatabase (SQLDatabase):

    CACHE_FILE = "/var/eix/cache"

    def __init__ (self, session):
        SQLDatabase.__init__(self, session)

        if "cache" not in session:
            self.cache = self.CACHE_FILE
            session["cache"] = self.cache
        else:
            self.cache = session["cache"]

        debug("Using '%s' as eix cache file.", self.cache)

    def updated (self):
        mtime = os.stat(self.cache).st_mtime
        old = self.session.get("mtime", 0)
        
        self.session["mtime"] = mtime

        return old < mtime

    @SQLDatabase.con
    def populate (self, category = None, connection = None):
        inst = system.find_packages(pkgSet = system.SET_INSTALLED, key = category, with_version = False)

        def _get():
            with EixReader(self.cache) as eix:
                for cat in eix.categories:
                    if category is None or cat.name() == category:
                        for pkg in cat.packages():
                            yield (cat.name(), pkg.name(), pkg.name() in inst, False)

        connection.executemany("INSERT INTO packages (cat, name, inst, disabled) VALUES (?, ?, ?, ?)", _get())
        connection.commit()
