# -*- coding: utf-8 -*-
#
# File: portato/eix/exceptions.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

class EixError (Exception):
    message = _("Unknown error.")

    def __str__ (self):
        return self.message

class EndOfFileException (EixError):

    def __init__ (self, filename):
        self.message = _("End of file reached though it was not expected: '%s'") % filename

class UnsupportedVersionError (EixError):

    def __init__ (self, version):
        self.message = _("Version '%s' is not supported.") % version
