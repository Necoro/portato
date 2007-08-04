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

import gtk
from portato import plugin
from portato.backend import system
from windows import MainWindow, SearchWindow, EbuildWindow
from uncaughtException import register_ex_handler

def run ():
	try:
		m = MainWindow()
		register_ex_handler()
		m.main()
	except KeyboardInterrupt:
		pass

def show_ebuild (pkg):
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
