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

"""
A module to parse the eix-cache files.
"""

from __future__ import absolute_import, with_statement
__docformat__ = "restructuredtext"

from . import parser
from .exceptions import UnsupportedVersionError

from ..helper import debug

class EixReader(object):
    """
    The main class to use to have access to the eix-cache.

    Note that the file used internally stays open during the whole operation.
    So please call `close()` when you are finished.

    The ``EixReader`` supports the context manager protocol, so you can the ``with ... as ...``.

    :CVariables:

        supported_versions : int[]
            The list of versions of the eix-cache, which are supported by this reader.

    :IVariables:

        file : file
            The eix cache file.

        header : `parser.header`
            The header of the eix cache.

        categories : `parser.category` []
            The list of categories.
    """

    supported_versions = (28,)
        
    def __init__ (self, filename):
        """
        :param filename: Path to the cache file
        :type filename: string
        """

        self.file = open(filename, "r")
        
        try:
            version = parser.number(self.file)

            if version not in self.supported_versions:
                raise UnsupportedVersionError(self.version)

            debug("Started EixReader for version %s.", version)

            self.file.seek(0)

            self.header = parser.header(self.file)
            self.categories = parser.vector(self.file, parser.category, nelems = self.header.ncats())
        except:
            self.close()
            raise

    def __enter__ (self):
        return self

    def __exit__ (self, exc_type, exc_val, exc_tb):
        self.close()

    def close (self):
        """
        Closes the cache file.
        """
        self.file.close()
        debug("EixReader closed.")
