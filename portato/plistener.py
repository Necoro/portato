# -*- coding: utf-8 -*-
#
# File: portato/plistener.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import os
from subprocess import Popen

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

	def set_recv (self, mem, sig, rw):
		self._mem = mem
		self._sig = sig
		self._rw = rw

		while True:
			try:
				try:
					self._sig.P()
					self._rw.P()
					len = self._mem.read(NumberOfBytes = 4)
					string = self._mem.read(NumberOfBytes = int(len), offset = 4)
				finally:
					self._rw.V()

				data = string.split("\0")

				if data[0] == "notify":
					self.do_notify(*data[1:])
				elif data[0] == "cmd":
					self.do_cmd(data[1:])
				elif data[0] == "close":
					break
			except KeyboardInterrupt:
				debug("Got KeyboardInterrupt. Aborting.")
				break

		self._mem.remove()
		self._sig.remove()
		self._rw.remove()

	def do_cmd (self, cmdlist):
		"""Starts a command as the user.
		
		@param cmdlist: list of command (options)
		@type cmdlist: string[]"""

		Popen(cmdlist)

	def do_notify(self, base, descr, icon, urgency = None):
		"""Displays a notify.
		This will do nothing if pynotify is not present and/or root is running the listener."""

		if pynotify and os.getuid() != 0:
			if not pynotify.is_initted():
				pynotify.init(APP)

			n = pynotify.Notification(base, descr, icon)
			if urgency is not None and urgency != "":
				n.set_urgency(int(urgency))
			n.show()

	def set_send (self, mem = None, sig = None, rw = None):
		if mem is None or sig is None or rw is None:
			warning(_("Listener has not been started."))
			self._mem = None
			self._sig = None
			self._rw = None
		else:
			import shm_wrapper as shm

			self._mem = shm.SharedMemoryHandle(mem)
			self._sig = shm.SemaphoreHandle(sig)
			self._rw = shm.SemaphoreHandle(rw)

	def __send (self, string):
		self._rw.P()
		self._sig.Z()
		try:
			self._mem.write("%4d%s" % (len(string), string))
			self._sig.V()
		finally:
			self._rw.V() 

	def send_notify (self, base = "", descr = "", icon = "", urgency = None):	
		if self._sig is None:
			self.do_notify(base, descr, icon, urgency)
		else:
			string = "\0".join(["notify", base, descr, icon])

			if urgency is not None:
				string += "\0%d" % urgency
			else:
				string += "\0"

			self.__send(string)

	def send_cmd (self, cmdlist):
		if self._sig is None:
			self.do_cmd(cmdlist)
		else:
			self.__send("\0".join(["cmd"] +cmdlist))

	def close (self):
		if self._sig is not None:
			self.__send("close")
