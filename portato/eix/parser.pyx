# -*- coding: utf-8 -*-
#
# File: portato/eix/_parser.pyx
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
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

__docformat__ = "restructuredtext"

cdef extern from "stdio.h":
    ctypedef struct FILE:
        pass

    int fgetc(FILE* stream)
    long ftell(FILE* stream)
    int fseek(FILE* stream, long offset, int whence)
    
    int EOF
    int SEEK_CUR

cdef extern from "Python.h":
    FILE* PyFile_AsFile(object)

ctypedef unsigned char UChar
ctypedef long long LLong

from portato.eix.exceptions import EndOfFileException

#
# Helper
#

cdef int _get_byte (FILE* file) except -1:
    cdef int c = fgetc(file)

    if c == EOF:
        raise EndOfFileException

    return c

#
# Base Types
#

cdef LLong _number (object pfile):
    cdef UChar n
    cdef LLong value
    cdef int i
    
    cdef unsigned short count = 1
    cdef FILE* file = PyFile_AsFile(pfile)

    n = <UChar>_get_byte(file)

    if n < 0xFF:
        return <LLong>n
    else:

        n = <UChar>_get_byte(file)
        while (n == 0xFF):
            count += 1
            n = <UChar>_get_byte(file)

        if n == 0:
            value = <LLong>0xFF # 0xFF is encoded as 0xFF 0x00
            count -= 1
        else:
            value = <LLong>n
        
        for i in range(count):
            value = (value << 8) | <LLong>(_get_byte(file))
        
    return value

def number (file):
    """
    Returns a number.

    :param file: The file to read from
    :type file: file
    :rtype: int
    """

    return _number(file)

def vector (file, get_type, nelems = None):
    """
    Returns a vector of elements.

    :Parameters:

        file : file
            The file to read from.

        get_type : function(file, bool)
            The function determining type of the elements.

        nelems : int
            Normally the eix-Vector has the number of elements as the first argument.
            If for some reason this is not the case, you can pass it in here.

    :rtype: list
    """

    cdef LLong n
    cdef LLong i

    if nelems is None:
        n = _number(file)
    else:
        n = nelems
    
    l = []
    for i in range(n):
        l.append(get_type(file))
    
    return l

def string (file):
    """
    Returns a string.

    :param file: The file to read from
    :type file: file
    :rtype: str
    """
    nelems = _number(file)

    s = file.read(nelems)

    if len(s) != nelems:
        raise EndOfFileException, file.name

    return s

#
# Complex Types
#

cdef class overlay:
    """
    Represents an overlay object.

    :IVariables:

        path : string
            The path to the overlay

        label : string
            The label/name of the overlay
    """

    cdef readonly object path
    cdef readonly object label

    def __init__ (self, file):
        """
        :param file: The file to read from
        :type file: file
        """
        
        self.path = string(file)
        self.label = string(file)

cdef class header:
    """
    Represents the header of the cache.

    :IVariables:

        version : int
            The version of the cache file.

        ncats : int
            The number of categories.

        overlays : `overlay` []
            The list of overlays.

        provide : string[]
            A list of "PROVIDE" values.

        licenses : string[]
            The list of licenses.

        keywords : string[]
            The list of keywords.
        
        useflags : string[]
            The list of useflags.
        
        slots : string[]
            The list of slots different from "0".

        sets : string[]
            The names of world sets are the names (without leading @) of the world sets stored in /var/lib/portage/world_sets.
            If SAVE_WORLD=false, the list is empty.
    """
    
    cdef readonly object version
    cdef readonly object ncats
    cdef readonly object overlays
    cdef readonly object provide
    cdef readonly object licenses
    cdef readonly object keywords
    cdef readonly object useflags
    cdef readonly object slots
    cdef readonly object sets

    def __init__ (self, file):
        """
        :param file: The file to read from
        :type file: file
        """
        self.version = _number(file)
        self.ncats = _number(file)
        self.overlays = vector(file, overlay)
        self.provide = vector(file, string)
        self.licenses = vector(file, string)
        self.keywords = vector(file, string)
        self.useflags = vector(file, string)
        self.slots = vector(file, string)
        self.sets = vector(file, string)

cdef class package:
    """
    The representation of one package.

    Currently, version information is not parsed and stored.
    So you can gain general infos only.

    :IVariables:
        
        name : string
            The name of the package.

        description : string
            Description of the package.

        homepage : string
            The homepage of the package.

        provide : int[]
            The indices of `header.provide` representing the PROVIDE value of the package.

        license : int
            The index of `header.licenses` representing the license of the package.

        useflags : int[]
            The indices of `header.useflags` representing the IUSE value of the package.
    """

    cdef LLong _offset
    cdef readonly object name
    cdef readonly object description
    cdef readonly object provide
    cdef readonly object homepage
    cdef readonly object license
    cdef readonly object useflags

    def __init__ (self, file):
        """
        :param file: The file to read from
        :type file: file
        """
        cdef FILE* cfile = PyFile_AsFile(file)
        cdef long after_offset
        
        self._offset = _number(file)
        
        after_offset = ftell(cfile)
        
        self.name = string(file)
        self.description = string(file)
        self.provide = vector(file, number)
        self.homepage = string(file)
        self.license = number(file)
        self.useflags = vector(file, number)
        
        # self.versions = LE(typed_vector(version))
        # for the moment just skip the versions
        fseek(cfile, self._offset - (ftell(cfile) - after_offset), SEEK_CUR)

cdef class category:
    """
    Represents a whole category.

    :IVariables:

        name : string
            The category name.

        packages : `package` []
            All the packages of the category.
    """
    
    cdef readonly object name
    cdef readonly object packages

    def __init__ (self, file):
        """
        :param file: The file to read from
        :type file: file
        """
        self.name = string(file)
        self.packages = vector(file, package)
