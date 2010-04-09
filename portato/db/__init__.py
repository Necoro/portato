# -*- coding: utf-8 -*-
#
# File: portato/db/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from . import database as db
from .exceptions import UnknownDatabaseTypeError, DatabaseInstantiationError
from ..session import Session, SectionDict
from ..helper import debug, warning, error

types = {
        "sql": (_("SQLite"), _("Uses an SQLite-database to store package information.\nMay take longer to generate at the first time, but has advantages if portato is re-started with an unchanged portage tree. Additionally it allows to use fast SQL expressions for fetching the data.")),
        "dict": (_("Hashmap"), _("Uses an in-memory hashmap to store package information.\nHas been used since at least version 0.3.3, but all information has to be regenerated on each startup.")),
        "eixsql" : (_("eix + SQLite"), _("Similar to SQLite, but now uses the eix database to get the package information.\nThis should be much faster on startup, but requires that your eix database is always up-to-date.\nAdditionally, this is the only database allowing searching in descriptions."))
        }

class Database(db.Database):
    DEFAULT = "dict"

    def __new__ (cls, type = None):
        if not '_the_instance' in cls.__dict__:
            dbcls = cls._generate(type)
            cls._the_instance = dbcls(cls._get_session())
        elif type is not None:
            raise DatabaseInstantiationError("Database instantiation called with 'type' argument multiple times.")
        return cls._the_instance
    
    @classmethod
    def _generate(cls, type):

        if type is None:
            warning("No database type specified! Falling back to default.")
            type = cls.DEFAULT
        
        cls.DB_TYPE = type

        if type == "sql":
            debug("Using SQLDatabase")
            try:
                from .sql import SQLDatabase
            except ImportError:
                warning(_("Cannot load %s."), "SQLDatabase")
                return cls._generate("dict")
            else:
                return SQLDatabase

        elif type == "dict":
            debug("Using HashDatabase")
            from .hash import HashDatabase
            return HashDatabase
        
        elif type == "eixsql":
            debug("Using EixSQLDatabase")
            try:
                from .eix_sql import EixSQLDatabase
            except ImportError:
                warning(_("Cannot load %s."), "EixSQLDatabase.")
                return cls._generate("sql")
            else:
                return EixSQLDatabase

        else:
            error(_("Unknown database type: %s"), type)
            raise UnknownDatabaseTypeError, type

    @classmethod
    def _get_session(cls):
        return SectionDict(Session("db.session", name = "DB", oldfiles = ["db.cfg"]), cls.DB_TYPE)
