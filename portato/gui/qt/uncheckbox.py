# -*- coding: utf-8 -*-
#
# File: portato/gui/qt/uncheckbox.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from PyQt4.QtGui import QCheckBox
from PyQt4.QtCore import Qt

class UncheckBox (QCheckBox):
	"""A checkbox which looks like a normal one, but cannot be checked by the user.
	Focusing and hovering are disabled too."""

	def __init__ (self, *args):
		QCheckBox.__init__(self, *args)
		self.setFocusPolicy(Qt.NoFocus)

	def mousePressEvent (self, event):
		if event.button() == Qt.LeftButton: # ignore leftbutton clicks
			pass
		else:
			QCheckBox.mousePressEvent(self, event)

	def keyPressEvent (self, event):
		if event.key() == Qt.Key_Space: # ignore space
			pass
		else:
			QCheckBox.keyPressEvent(self, event)

	def enterEvent (self, event):
		# disable hovering - this is set to True somewhere I cannot fix ;)
		self.setAttribute(Qt.WA_Hover, False)
