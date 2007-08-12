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

import socket, os
from subprocess import Popen
from gettext import lgettext as _

try:
	import pynotify
except ImportError:
	pynotify = None

from constants import SOCKET, APP
from helper import debug, warning

class PListener (object):
	"""This class handles the communication between the "listener" and the GUI.
	This listener starts programs as the user while the GUI runs as root.
	
	@ivar _recv: listener socket
	@type _recv: socket.socket
	@ivar _send: sender socket
	@type _send: socket.socket"""

	def set_recv (self):
		self._recv = socket.socket(socket.AF_UNIX)

		try:
			self._recv.bind(SOCKET)
		except socket.error, e:
			if int(e[0]) == 98: # already existing - delete
				os.unlink(SOCKET)
				self._recv.bind(SOCKET)
			else:
				raise

		self._recv.listen(1)
		con, addr = self._recv.accept()
		
		while True:
			try:
				len = con.recv(4)
				string = con.recv(int(len))

				data = string.split("\0")

				if data[0] == "notify":
					self.do_notify(*data[1:])
				elif data[0] == "cmd":
					self.do_cmd(data[1:])
				elif data[0] == "close":
					break
			except KeyboardInterrupt:
				pass

		con.close()
		self._recv.close()

	def do_cmd (self, cmdlist):
		"""Starts a command as the user.
		
		@param cmdlist: list of command (options)
		@type cmdlist: string[]"""

		Popen(cmdlist)

	def do_notify(self, base, descr, icon, urgency):
		"""Displays a notify.
		This will do nothing if pynotify is not present and/or root is running the listener."""

		if pynotify and not os.getuid == 0:
			if not pynotify.is_initted():
				pynotify.init(APP)

			n = pynotify.Notification(base, descr, icon)
			n.set_urgency(int(urgency))
			n.show()

	def set_send (self):
		self._send = socket.socket(socket.AF_UNIX)
		try:
			self._send.connect(SOCKET)
		except socket.error, e:
			if e[0] in [111, 2]: # can't connect
				warning(_("Listener has not been started."))
				self._send = None
			else:
				raise

	def __send (self, string):
		self._send.sendall("%4d" % len(string))
		self._send.sendall(string)

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
			self._send.close()
			os.unlink(SOCKET)
