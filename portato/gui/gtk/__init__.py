# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from gettext import lgettext as _

from ... import get_listener
from .exception_handling import register_ex_handler

def run ():
	from .splash import SplashScreen
	try:
		s = SplashScreen(_("Loading Portage"))
		register_ex_handler()
		s.show()
		from .windows import MainWindow
		m = MainWindow(s)
		s.hide()
		m.main()
	except KeyboardInterrupt:
		pass

	get_listener().close()

def show_ebuild (pkg):	
	import gtk
	from ... import plugin
	from ...backend import system
	from .windows import SearchWindow, EbuildWindow

	plugin.load_plugins("gtk")
	register_ex_handler()

	def _show (pkg):
		gtk.main_quit()

		pkg = system.new_package(pkg)
		hook = plugin.hook("open_ebuild", pkg, None)
		
		ew = hook(EbuildWindow)(None, pkg)
		ew.window.connect("destroy", lambda *x: gtk.main_quit())
		ew.window.set_title("Portato Ebuild Viewer - %s" % pkg.get_cpv())
		
		gtk.main()
	
	s = SearchWindow(None, [x.get_cpv() for x in system.sort_package_list(system.find_all_packages(pkg, True))], _show)
	s.window.set_title("Portato Ebuild Viewer - Search")
	s.window.connect("destroy", lambda *x: gtk.main_quit())
	
	gtk.main()
