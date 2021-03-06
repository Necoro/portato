# -*- coding: utf-8 -*-
#
# File: portato/eix/exceptions.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

"""
Different exceptions used in the eix module.
"""


__docformat__ = "restructuredtext"

class EixError (Exception):
    """
    The base class for all exceptions of this module.

    :ivar message: The error message
    """

    message = _("Unknown error.")
    
    def __init__ (self, msg = None):
        Exception.__init__(self)
        
        if msg:
            self.message = msg

    def __str__ (self):
        return self.message

class EndOfFileException (EixError):
    """
    Denotes the unexpected EOF.
    """

    def __init__ (self, filename):
        EixError.__init__(self,  _("End of file reached though it was not expected: '%s'") % filename)

class UnsupportedVersionError (EixError):
    """
    The version of the cache file found is not supported.
    """

    def __init__ (self, version):
        EixError.__init__(self, _("Version '%s' is not supported.") % version)
