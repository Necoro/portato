# -*- coding: utf-8 -*-
#
# File: portato/backend/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from ..helper import debug
from .system_interface import SystemInterface
from .exceptions import BlockedException, PackageNotFoundException, DependencyCalcError, InvalidSystemError

class _Package (object):
    """Wrapping class from which L{portato.backend.Package} inherits. This is used by the flags module to check
    whether an object is a package. It cannot use the normal Package class as this results in cyclic dependencies."""

    def __init__ (self):
        raise TypeError, "Calling __init__ on portato.backend._Package objects is not allowed."

def is_package(what):
    return isinstance(what, _Package)

class SystemWrapper (SystemInterface):
    """This is a wrapper to the different system interfaces, allowing the direct import via C{from portato.backend import system}.
    With this wrapper a change of the system is propagated to all imports."""
    
    __system = 'portage'
    __wrapped_sys = None
    __slots__ = ('__system', '__wrapped_sys', 'set_system', '__load')

    def __getattribute__ (self, name):
        """Just pass all attribute accesses directly to _sys."""

        if name in SystemWrapper.__slots__:
            return object.__getattribute__(self, name)
        
        if SystemWrapper.__wrapped_sys is None:
            SystemWrapper.__load()

        return getattr(SystemWrapper.__wrapped_sys, name)

    @classmethod
    def set_system (cls, system):
        """Sets the current system to a new one.

        @param system: the name of the system to take
        @type system: string"""

        cls.__system = system
        cls.__wrapped_sys = None

    @classmethod
    def __load (cls):
        """Loads the current chosen system.

        @raises InvalidSystemError: if an inappropriate system is set"""
        if cls.__system == "portage":
            debug("Setting Portage System")
            from .portage import PortageSystem
            cls.__wrapped_sys = PortageSystem ()
        else:
            raise InvalidSystemError, cls.__system

system = SystemWrapper()
