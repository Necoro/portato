# -*- coding: utf-8 -*-
#
# File: portato/eix/parser.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import os
import struct
from functools import partial

from ..helper import debug
from .exceptions import EndOfFileException

def _get_bytes (file, length, expect_list = False):
    s = file.read(length)

    if len(s) != length:
        raise EndOfFileException, file.name

    if length == 1 and not expect_list:
        return ord(s) # is faster than unpack and we have a scalar
    else:
        return struct.unpack("%sB" % length, s)

def number (file, skip = False):
    n = _get_bytes(file, 1)

    if n < 0xFF:
        value = n
    else:
        count = 0

        while (n == 0xFF):
            count += 1
            n = _get_bytes(file, 1)

        if n == 0:
            n = 0xFF # 0xFF is encoded as 0xFF 0x00
            count -= 1
        
        value = n << (count*8)

        if count > 0:

            if skip:
                file.seek(count, os.SEEK_CUR)
                return
            
            else:
                rest = _get_bytes(file, count, expect_list = True)

                for i, r in enumerate(rest):
                    value += r << ((count - i - 1)*8)
        
    return value

def vector (file, get_type, skip = False, nelems = None):
    if nelems is None:
        nelems = number(file)
    
    if skip:
        for i in range(nelems):
            get_type(file, skip = True)
    else:
        return [get_type(file) for i in range(nelems)]

def typed_vector(type, nelems = None):
    if nelems is None:
        return partial(vector, get_type = type)
    else:
        return partial(vector, get_type = type, nelems = nelems)

def string (file, skip = False):
    nelems = number(file)

    if skip:
        file.seek(nelems, os.SEEK_CUR)
        return
    else:
        s = file.read(nelems)

    if len(s) != nelems:
        raise EndOfFileException, file.name

    return s

class LazyElement (object):
    __slots__ = ("file", "get_type", "_value", "pos")
    
    def __init__ (self, get_type, file):
        self.file = file
        self.get_type = get_type
        self._value = None

        self.pos = file.tell()
        get_type(file, skip=True) # skip it for the moment

    @property
    def value (self):
        if self._value is None:
            old_pos = self.file.tell()
            self.file.seek(self.pos, os.SEEK_SET)
            self._value = self.get_type(self.file, skip = False)
            self.file.seek(old_pos, os.SEEK_SET)
        
        return self._value

    def __call__ (self):
        return self.value

class overlay (object):
    __slots__ = ("path", "label")

    def __init__ (self, file, skip = False):
        self.path = LazyElement(string, file)
        self.label = LazyElement(string, file)

class header (object):
    __slots__ = ("version", "ncats", "overlays", "provide",
            "licenses", "keywords", "useflags", "slots", "sets")

    def __init__ (self, file, skip = False):
        def LE (t):
            return LazyElement(t, file)

        self.version = LE(number)
        self.ncats = LE(number)
        self.overlays = LE(typed_vector(overlay))
        self.provide = LE(typed_vector(string))
        self.licenses = LE(typed_vector(string))
        self.keywords = LE(typed_vector(string))
        self.useflags = LE(typed_vector(string))
        self.slots = LE(typed_vector(string))
        self.sets = LE(typed_vector(string))

class package (object):
    __slots__ = ("offset","name", "description",
            "provide", "homepage", "license", "useflags")

    def __init__ (self, file, skip = False):
        def LE (t):
            return LazyElement(t, file)
        
        self.offset = number(file)
        
        after_offset = file.tell()
        
        self.name = LE(string)
        self.description = LE(string)
        self.provide = LE(typed_vector(number))
        self.homepage = LE(string)
        self.license = LE(number)
        self.useflags = LE(typed_vector(number))
        
        # self.versions = LE(typed_vector(version))
        # for the moment just skip the versions
        file.seek(self.offset - (file.tell() - after_offset), os.SEEK_CUR)

class category (object):
    __slots__ = ("name", "packages")

    def __init__ (self, file, skip = False):
        self.name = LazyElement(string, file)
        self.packages = LazyElement(typed_vector(package), file)
