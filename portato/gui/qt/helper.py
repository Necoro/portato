# -*- coding: utf-8 -*-
#
# File: portato/gui/qt/helper.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from PyQt4 import Qt

def qCheck (check):
	"""Maps True or False to Qt.Checked or Qt.Unchecked.
	
	@param check: boolean value
	@type check: bool
	@returns: CheckState-Constant
	@rtype: int"""

	if check:
		return Qt.Qt.Checked
	else:
		return Qt.Qt.Unchecked

def qIsChecked (check):
	"""Maps Qt.Checked and Qt.Unchecked to True and False.
	
	@param check: CheckState-Constant
	@type check: int
	@returns: appropriate boolean value
	@rtype: bool"""
	return check == Qt.Qt.Checked
