# -*- coding: utf-8 -*-
#
# File: portato/gui/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from ..helper import _
from .. import get_listener
from .exception_handling import register_ex_handler

def run ():
	from .windows.splash import SplashScreen
	try:
		s = SplashScreen(_("Loading Backend"))
		register_ex_handler()
		s.show()
		from .windows.main import MainWindow
		m = MainWindow(s)
		s.hide()
		m.main()
	except KeyboardInterrupt:
		pass

	get_listener().close()
