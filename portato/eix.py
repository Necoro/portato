# -*- coding: utf-8 -*-
#
# File: portato/eix.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import struct
from functools import wraps

from .helper import debug

class EixError (Exception):
    message = "Unknown error."

    def __str__ (self):
        return self.message

class EndOfFileException (EixError):

    def __init__ (self, filename):
        self.message = "End of file reached though it was not expected: '%s'" % filename

class EixReaderClosed (EixError):
    message = "EixReader is already closed."

class UnsupportedVersionError (EixError):

    def __init__ (self, version):
        self.message = "Version '%s' is not supported." % version

class EixReader (object):
    supported_versions = (28, )

    def __init__ (self, filename):
        self.filename = filename
        self.file = open(filename, "r")
        self.closed = 0
        
        try:
            self.version = self.get_number()

            if self.version not in self.supported_versions:
                raise UnsupportedVersionError(self.version)

            debug("Started EixReader for version %s.", self.version)
        except:
            self.close()
            raise

    def check_closed (f):
        @wraps(f)
        def wrapper (self, *args, **kwargs):
            if self.closed:
                raise EixReaderClosed

            return f(self, *args, **kwargs)
        return wrapper

    @check_closed
    def get_number (self):
        n = self._get_bytes(1)

        if n < 0xFF:
            value = n
        else:
            count = 0

            while (n == 0xFF):
                count += 1
                n = self._get_bytes(1)

            if n == 0:
                n = 0xFF # 0xFF is encoded as 0xFF 0x00
                count -= 1
            
            value = n << (count*8)

            if count > 0:
                rest = self._get_bytes(count, expect_list = True)

                for i, r in enumerate(rest):
                    value += r << ((count - i - 1)*8)
            
        return value

    def _get_bytes (self, length, expect_list = False):
        s = self.file.read(length)

        if len(s) != length:
            raise EndOfFileException, self.filename

        if length == 1 and not expect_list:
            return ord(s) # is faster than unpack and we have a scalar
        else:
            return struct.unpack("%sB" % length, s)

    @check_closed
    def close (self):
        if self.closed:
            raise EixReaderClosed
        
        self.file.close()
        self.closed = 1
        
        debug("EixReader closed.")
