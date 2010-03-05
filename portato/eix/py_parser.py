# -*- coding: utf-8 -*-
#
# File: portato/eix/parser.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

"""
The cache file supports different types of data.
In this module (nearly) all of these types have a corresponding function.

For the exact way all the functions work, have a look at the eix format description.
"""

from __future__ import absolute_import, with_statement
__docformat__ = "restructuredtext"

import os
import struct
from functools import partial

from ..helper import debug
from .exceptions import EndOfFileException

#
# Helper
#

def _get_bytes (file, length, expect_list = False):
    """
    Return a number of bytes.
    
    :Parameters:

        file : file
            The file to read from.

        length : int
            The number of bytes to read.

        expect_list : bool
            In case ``length`` is 1, only a single byte is returned. If ``expect_list`` is true, then a list is also returned in this case.

    :rtype: int or int[]
    :raises EndOfFileException: if EOF is reached during execution
    """

    s = file.read(length)

    if len(s) != length:
        raise EndOfFileException, file.name

    if length == 1 and not expect_list:
        return ord(s) # is faster than unpack and we have a scalar
    else:
        return struct.unpack("%sB" % length, s)

#
# Base Types
#

def number (file, skip = False):
    """
    Returns a number.

    :Parameters:

        file : file
            The file to read from.

        skip : bool
            Do not return the actual value, but just skip to the next datum.

    :rtype: int
    """

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
    """
    Returns a vector of elements.

    :Parameters:

        file : file
            The file to read from.

        get_type : function(file, bool)
            The function determining type of the elements.

        skip : bool
            Do not return the actual value, but just skip to the next datum.

        nelems : int
            Normally the eix-Vector has the number of elements as the first argument.
            If for some reason this is not the case, you can pass it in here.

    :rtype: list
    """

    if nelems is None:
        nelems = number(file)
    
    if skip:
        for i in range(nelems):
            get_type(file, skip = True)
    else:
        return [get_type(file) for i in range(nelems)]

def typed_vector(type, nelems = None):
    """
    Shortcut to create a function for a special type of vector.

    :Parameters:

        type : function(file, bool)
            The function determining type of the elements.

        nelems : int
            Normally the eix-Vector has the number of elements as the first argument.
            If for some reason this is not the case, you can pass it in here.
            Do not return the actual value, but just skip to the next datum.

    :rtype: function(file, bool)
    :see: `vector`
    """

    if nelems is None:
        return partial(vector, get_type = type)
    else:
        return partial(vector, get_type = type, nelems = nelems)

def string (file, skip = False):
    """
    Returns a string.

    :Parameters:

        file : file
            The file to read from.

        skip : bool
            Do not return the actual value, but just skip to the next datum.

    :rtype: str
    """
    nelems = number(file)

    if skip:
        file.seek(nelems, os.SEEK_CUR)
        return
    else:
        s = file.read(nelems)

    if len(s) != nelems:
        raise EndOfFileException, file.name

    return s

#
# Complex Types
#

class LazyElement (object):
    """
    This class models a value in the cache, which is only read on access.

    If not accessed directly, only the position inside the file is stored.
    """
    __slots__ = ("file", "get_type", "_value", "pos")
    
    def __init__ (self, get_type, file):
        """
        :Parameters:

            get_type : function(file, bool)
                The function determining type of the elements.

            file : file
                The file to read from.
        """

        self.file = file
        self.get_type = get_type
        self._value = None

        self.pos = file.tell()
        get_type(file, skip=True) # skip it for the moment

    @property
    def value (self):
        """
        The value of the element.
        """

        if self._value is None:
            old_pos = self.file.tell()
            self.file.seek(self.pos, os.SEEK_SET)
            self._value = self.get_type(self.file, skip = False)
            self.file.seek(old_pos, os.SEEK_SET)
        
        return self._value

    def __call__ (self):
        """
        Convenience function. Also returns the value.
        """
        return self.value

class overlay (object):
    """
    Represents an overlay object.

    :IVariables:

        path : `LazyElement` <string>
            The path to the overlay

        label : `LazyElement` <string>
            The label/name of the overlay
    """
    __slots__ = ("path", "label")

    def __init__ (self, file, skip = False):
        """
        :Parameters:

            file : file
                The file to read from.

            skip : bool
                Do not return the actual value, but just skip to the next datum.
        """
        
        self.path = LazyElement(string, file)
        self.label = LazyElement(string, file)

class header (object):
    """
    Represents the header of the cache.

    :IVariables:

        version : `LazyElement` <int>
            The version of the cache file.

        ncats : `LazyElement` <int>
            The number of categories.

        overlays : `LazyElement` <`overlay` []>
            The list of overlays.

        provide : `LazyElement` <string[]>
            A list of "PROVIDE" values.

        licenses : `LazyElement` <string[]>
            The list of licenses.

        keywords : `LazyElement` <string[]>
            The list of keywords.
        
        useflags : `LazyElement` <string[]>
            The list of useflags.
        
        slots : `LazyElement` <string[]>
            The list of slots different from "0".

        sets : `LazyElement` <string[]>
            The names of world sets are the names (without leading @) of the world sets stored in /var/lib/portage/world_sets.
            If SAVE_WORLD=false, the list is empty.
    """
    __slots__ = ("version", "ncats", "overlays", "provide",
            "licenses", "keywords", "useflags", "slots", "sets")

    def __init__ (self, file, skip = False):
        """
        :Parameters:

            file : file
                The file to read from.

            skip : bool
                Do not return the actual value, but just skip to the next datum.
        """
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
    """
    The representation of one package.

    Currently, version information is not parsed and stored.
    So you can gain general infos only.

    :IVariables:
        
        name : `LazyElement` <string>
            The name of the package.

        description : `LazyElement` <string>
            Description of the package.

        homepage : `LazyElement` <string>
            The homepage of the package.

        provide : `LazyElement` <int[]>
            The indices of `header.provide` representing the PROVIDE value of the package.

        license : `LazyElement` <int>
            The index of `header.licenses` representing the license of the package.

        useflags : `LazyElement` <int[]>
            The indices of `header.useflags` representing the IUSE value of the package.
    """

    __slots__ = ("_offset", "name", "description", "provide",
            "homepage", "license", "useflags")

    def __init__ (self, file, skip = False):
        """
        :Parameters:

            file : file
                The file to read from.

            skip : bool
                Do not return the actual value, but just skip to the next datum.
        """
        def LE (t):
            return LazyElement(t, file)
        
        self._offset = number(file)
        
        after_offset = file.tell()
        
        self.name = LE(string)
        self.description = LE(string)
        self.provide = LE(typed_vector(number))
        self.homepage = LE(string)
        self.license = LE(number)
        self.useflags = LE(typed_vector(number))
        
        # self.versions = LE(typed_vector(version))
        # for the moment just skip the versions
        file.seek(self._offset - (file.tell() - after_offset), os.SEEK_CUR)

class category (object):
    """
    Represents a whole category.

    :IVariables:

        name : `LazyElement` <string>
            The category name.

        packages : `LazyElement` <`package` []>
            All the packages of the category.
    """
    __slots__ = ("name", "packages")

    def __init__ (self, file, skip = False):
        """
        :Parameters:

            file : file
                The file to read from.

            skip : bool
                Do not return the actual value, but just skip to the next datum.
        """
        self.name = LazyElement(string, file)
        self.packages = LazyElement(typed_vector(package), file)
