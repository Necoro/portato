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

from system_interface import SystemInterface

SYSTEM = "portage"
_sys = None

class SystemWrapper (object, SystemInterface):
	def __getattribute__ (self, name):
		global _sys
		return eval ("_sys.%s" % name)

def set_system (new_sys):
	global SYSTEM
	SYSTEM = new_sys
	load_system()

def load_system ():
	global _sys

	if SYSTEM == "portage":
		from portato.backend.portage import PortageSystem
		_sys = PortageSystem ()

system = SystemWrapper()

from exceptions import *
from package import Package

load_system()

