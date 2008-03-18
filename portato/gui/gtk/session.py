# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/session.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from ...helper import debug, _

# the current version for saved sessions
# change this, whenever the change is incompatible with previous versions
SESSION_VERSION = 1

class SessionException (Exception):

	error = _("Version mismatch.")
	def __init__ (self, got, expected):
		self.got = got
		self.expected = expected

	def __str__ (self):
		return "%s %s" % (self.error, (_("Got '%d' - expected '%d'.") % (self.got, self.expected)))

class OldSessionException (SessionException):
	error = _("Current session format is too old.")

class NewSessionException (SessionException):
	error = _("Current session format is newer than this version supports.")
