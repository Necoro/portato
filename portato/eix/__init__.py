# -*- coding: utf-8 -*-
#
# File: portato/eix/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

from . import parser
from . import exceptions as ex

from ..helper import debug

class EixReader(object):
    supported_version = (28,)
        
    def __init__ (self, filename):
        self.filename = filename
        self.file = open(filename, "r")
        
        try:
            self.version = parser.number(self.file)

            if self.version not in self.supported_versions:
                raise ex.UnsupportedVersionError(self.version)

            debug("Started EixReader for version %s.", self.version)
        except:
            self.close()
            raise

    def close (self):
        self.file.close()
        debug("EixReader closed.")
