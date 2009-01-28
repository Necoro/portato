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
from ..constants import USE_SQL
from ..helper import debug

_SESSION = None

def Database():
    global _SESSION

    if _SESSION is None:
        _SESSION = Session("db.cfg", name = "DB")

    if USE_SQL:
        debug("Using SQLDatabase")
        from .sql import SQLDatabase
        return SQLDatabase(SectionDict(_SESSION, "SQL"))
    else:
        debug("Using DictDatabase")
        from .dict import DictDatabase
        return DictDatabase(SectionDict(_SESSION, "dict"))
