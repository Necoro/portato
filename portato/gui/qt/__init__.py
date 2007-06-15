# -*- coding: utf-8 -*-
#
# File: portato/gui/qt/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from portato import plugin
from portato.backend import system

from PyQt4.Qt import QApplication
from windows import MainWindow, EbuildDialog, SearchDialog

def run():
	app = QApplication([])
	m = MainWindow()
	app.exec_()

def show_ebuild (pkg):
	plugin.load_plugins("qt")	
	app = QApplication([])
	
	def _show (pkg):
		pkg = system.new_package(pkg)
		hook = plugin.hook("open_ebuild", pkg, None)
		
		ew = hook(EbuildDialog)(None, pkg)
		ew.setWindowTitle("Portato Ebuild Viewer - %s" % pkg.get_cpv())
		ew.exec_()
		
	s = SearchDialog(None, [x.get_cpv() for x in system.sort_package_list(system.find_all_packages(pkg, True))], _show)
	s.setWindowTitle("Portato Ebuild Viewer - Search")
	s.show()
	app.exec_()
