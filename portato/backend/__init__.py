# -*- coding: utf-8 -*-
#
# File: portato/backend/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from exceptions import *
from system_interface import SystemInterface

SYSTEM = "portage" # the name of the current system
_sys = None # the SystemInterface-instance

class SystemWrapper (SystemInterface):
	"""This is a wrapper to the different system interfaces, allowing the direct import via C{from portato.backend import system}.
	With this wrapper a change of the system is propagated to all imports."""
	
	def __getattribute__ (self, name):
		"""Just pass all attribute accesses directly to _sys."""
		return getattr(_sys, name)

def set_system (new_sys):
	"""Sets the current system to a new one.

	@param new_sys: the name of the system to take
	@type new_sys: string"""

	global SYSTEM
	SYSTEM = new_sys
	load_system()

def load_system ():
	"""Loads the current chosen system.

	@raises InvalidSystemError: if an inappropriate system is set"""
	
	global _sys

	if SYSTEM == "portage":
		from portato.backend.portage import PortageSystem
		_sys = PortageSystem ()
	else:
		raise InvalidSystemError, SYSTEM

system = SystemWrapper()

# import package before loading the system as some systems may depend on it being in the namespace
from package import Package

load_system()
