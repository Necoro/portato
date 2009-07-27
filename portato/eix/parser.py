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

from .helper import debug

from . import exceptions as ex

def _get_bytes (file, length, expect_list = False):
    s = file.read(length)

    if len(s) != length:
        raise EndOfFileException, file.name

    if length == 1 and not expect_list:
        return ord(s) # is faster than unpack and we have a scalar
    else:
        return struct.unpack("%sB" % length, s)

def number (file):
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
            rest = _get_bytes(file, count, expect_list = True)

            for i, r in enumerate(rest):
                value += r << ((count - i - 1)*8)
        
    return value

def vector (file, get_type, skip = False):
    nelems = number(file)
    
    if skip:
        for i in range(nelems):
            get_type(file, skip = True)
    else:
        return (get_type(file) for i in range(nelems))

def string (file, skip = False):
    nelems = number(file)

    if skip:
        file.seek(nelems, os.SEEK_CUR)
    else:
        s = file.read(nelems)

    if len(s) != nelems:
        raise EndOfFileException, file.name

    return s

def overlay (file, skip = False):
    if skip:
        string(file, skip = True) # path
        string(file, skip = True) # label
    else:
        return (string(file), string(file))
