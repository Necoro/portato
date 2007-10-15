# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/plistener.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import socket, os
from subprocess import Popen
from gettext import lgettext as _

try:
	import pynotify
except ImportError:
	pynotify = None

from .constants import APP
from .helper import debug, warning

class PListener (object):
	"""This class handles the communication between the "listener" and the GUI.
	This listener starts programs as the user while the GUI runs as root.
	
	@ivar _recv: listener socket
	@type _recv: int
	@ivar _send: sender socket
	@type _send: int"""

	def set_recv (self, pipe):
		self._recv = pipe

		while True:
			try:
				len = os.read(self._recv, 4)
				string = os.read(self._recv, int(len))

				data = string.split("\0")

				if data[0] == "notify":
					self.do_notify(*data[1:])
				elif data[0] == "cmd":
					self.do_cmd(data[1:])
				elif data[0] == "close":
					break
			except KeyboardInterrupt:
				break

		os.close(self._recv)

	def do_cmd (self, cmdlist):
		"""Starts a command as the user.
		
		@param cmdlist: list of command (options)
		@type cmdlist: string[]"""

		Popen(cmdlist)

	def do_notify(self, base, descr, icon, urgency):
		"""Displays a notify.
		This will do nothing if pynotify is not present and/or root is running the listener."""

		if pynotify and os.getuid() != 0:
			if not pynotify.is_initted():
				pynotify.init(APP)

			n = pynotify.Notification(base, descr, icon)
			n.set_urgency(int(urgency))
			n.show()

	def set_send (self, pipe = None):
		if pipe is None:
			warning(_("Listener has not been started."))
		
		self._send = pipe

	def __send (self, string):
		os.write(self._send, "%4d" % len(string))
		os.write(self._send, string)

	def send_notify (self, base = "", descr = "", icon = "", urgency = None):	
		if self._send is None:
			self.do_notify(base, descr, icon, urgency)
		else:
			string = "\0".join(["notify", base, descr, icon])

			if urgency is not None:
				string += "\0%d" % urgency
			else:
				string += "\0"

			self.__send(string)

	def send_cmd (self, cmdlist):
		if self._send is None:
			self.do_cmd(cmdlist)
		else:
			self.__send("\0".join(["cmd"] +cmdlist))

	def close (self):
		if self._send is not None:
			self.__send("close")
			os.close(self._send)
