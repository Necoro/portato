# -*- coding: utf-8 -*-
#
# File: portato/gui/qt/dialogs.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from PyQt4.QtGui import QMessageBox

def queue_not_empty_dialog(parent):
	return QMessageBox.question(parent, "Portato", "There are some packages in the emerge queue and/or an emerge process is running.\nDo you really want to quit?", QMessageBox.Ok | QMessageBox.Cancel)

def io_ex_dialog (parent, ex):
	string = ex.strerror
	if ex.filename:
		string = string+": "+ex.filename
	
	return QMessageBox.critical(parent, "Portato", string, QMessageBox.Ok)

def nothing_found_dialog (parent):
	return QMessageBox.information(parent, "Portato", "No packages found.", QMessageBox.Ok)

def not_root_dialog (parent):
	return QMessageBox.warning(parent, "Portato", "You are not root!", QMessageBox.Ok)

def unmask_dialog (parent, cpv):
	return QMessageBox.question(parent, "Portato", cpv+" seems to be masked.\nDo you want to unmask it and its dependencies?", QMessageBox.Yes | QMessageBox.No)

def blocked_dialog (parent, blocked, blocks):
	return QMessageBox.warning(parent, "Portato", blocked+" is blocked by "+blocks+".\nPlease unmerge the blocking package.", QMessageBox.Ok)

def remove_deps_dialog (parent):
	return QMessageBox.information(parent, "Portato", "You cannot remove dependencies. :)", QMessageBox.Ok)

def remove_queue_dialog (parent):
	return QMessageBox.question(parent, "Portato", "Do you really want to clear the whole queue?", QMessageBox.Yes | QMessageBox.No)

def changed_flags_dialog (parent, what = "flags"):
	return QMessageBox.information(parent, "Portato", "You have changed %s. Portato will write these changes into the appropriate files. Please backup them if you think it is necessairy." % what, QMessageBox.Ok)
