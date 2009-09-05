# -*- coding: utf-8 -*-
#
# File: portato/db/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from ..session import Session, SectionDict
from ..helper import debug, warning, error

class UnknownDatabaseTypeError (Exception):
    pass

_SESSION = None
_TYPE = None
_DEFAULT = "dict"
_DATABASE = None

types = {
        "sql": (_("SQLite"), _("Uses an SQLite-database to store package information.\nMay take longer to generate at the first time, but has advantages if portato is re-started with an unchanged portage tree. Additionally it allows to use fast SQL expressions for fetching the data.")),
        "dict": (_("Hashmap"), _("Uses an in-memory hashmap to store package information.\nHas been used since at least version 0.3.3, but all information has to be regenerated on each startup.")),
        "eixsql" : (_("eix + SQLite"), _("Similar to SQLite, but now uses the eix database to get the package information.\nThis should be much faster on startup, but requires that your eix database is always up-to-date."))
        }

def Database(type = None):
    global _SESSION, _TYPE, _DATABASE

    if type is None:
        if _DATABASE is None:
            warning("No database type specified! Falling back to default.")
            return Database(_DEFAULT)
        else:
            return _DATABASE
    
    if _SESSION is None:
        _SESSION = Session("db.cfg", name = "DB")
        _SESSION.load()

    _TYPE = type

    if type == "sql":
        debug("Using SQLDatabase")
        try:
            from .sql import SQLDatabase
        except ImportError:
            warning(_("Cannot load %s."), "SQLDatabase")
            _DATABASE = Database("dict")
        else:
            _DATABASE = SQLDatabase(SectionDict(_SESSION, type))

    elif type == "dict":
        debug("Using HashDatabase")
        from .hash import HashDatabase
        _DATABASE = HashDatabase(SectionDict(_SESSION, type))
    
    elif type == "eixsql":
        debug("Using EixSQLDatabase")
        try:
            from .eix_sql import EixSQLDatabase
        except ImportError:
            warning(_("Cannot load %s."), "EixSQLDatabase.")
            _DATABASE = Database("sql")
        else:
            _DATABASE = EixSQLDatabase(SectionDict(_SESSION, type))

    else:
        error(_("Unknown database type: %s"), type)
        raise UnknownDatabaseTypeError, type

    return _DATABASE
