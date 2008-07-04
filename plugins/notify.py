# -*- coding: utf-8 -*-
#
# File: plugins/notify.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

disable = False

try:
	import pynotify
except ImportError:
	disable = True

from portato import get_listener

from portato.helper import warning, error, debug
from portato.constants import APP_ICON, APP

class Notify (Plugin):
	__author__ = "René 'Necoro' Neumann"
	__description__ = "Show notifications when an emerge process finishes."
	__dependency__ = ["dev-python/notify-python"]

	def init (self):
		self.add_call("after_emerge", self.notify)

	def notify (self, retcode, **kwargs):
		if retcode is None:
			warning("NOTIFY :: %s", _("Notify called while process is still running!"))
		else:
			icon = APP_ICON
			if retcode == 0:
				text = _("Emerge finished!")
				descr = ""
				urgency = pynotify.URGENCY_NORMAL
			else:
				text = _("Emerge failed!")
				descr = _("Error Code: %d") % retcode
				urgency = pynotify.URGENCY_CRITICAL

			get_listener().send_notify(base = text, descr = descr, icon = icon, urgency = urgency)

register(Notify, disable)
