# -*- coding: utf-8 -*-
#
# File: portato/db/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from ..session import Session, SectionDict
from ..helper import debug

_SESSION = None
_TYPE = None

def _set_type(t):
    global _TYPE
    _TYPE = t

def Database():
    global _SESSION, _TYPE

    if _SESSION is None:
        _SESSION = Session("db.cfg", name = "DB")
        _SESSION.add_handler((["type"], _set_type, lambda: _TYPE), default = ["sql"])
        _SESSION.load()

    if _TYPE == "sql":
        debug("Using SQLDatabase")
        try:
            from .sql import SQLDatabase
        except ImportError:
            debug("Cannot load SQLDatabase.")
            _TYPE = "dict"
            return Database()
        else:
            return SQLDatabase(SectionDict(_SESSION, "SQL"))

    elif _TYPE == "dict":
        debug("Using DictDatabase")
        from .dict import DictDatabase
        return DictDatabase(SectionDict(_SESSION, "dict"))
