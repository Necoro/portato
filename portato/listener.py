# -*- coding: utf-8 -*-
#
# File: portato/listener.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
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

class Listener (object):
    """This class handles the communication between the "listener" and the GUI.
    This listener starts programs as the user while the GUI runs as root.
    
    @ivar _recv: listener socket
    @type _recv: int
    @ivar _send: sender socket
    @type _send: int"""

    def set_recv (self, _mq):

        self._mq = _mq

        while True:
            try:
                msg, type = self._mq.receive()

                data = msg.split("\0")
                debug("Listener received: %s", data)

                if data[0] == "notify":
                    self.do_notify(*data[1:])
                elif data[0] == "cmd":
                    self.do_cmd(data[1:])
                elif data[0] == "close":
                    break
            except KeyboardInterrupt:
                debug("Got KeyboardInterrupt. Aborting.")
                break

        self._mq = None
    
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

    def set_send (self, _mq = None):
        if _mq is None:
            warning(_("Listener has not been started."))
            self._mq = None
        else:
            from . import mq

            self._mq = mq.MessageQueue(_mq)

    def __send (self, string):
        self._mq.send(string)

    def send_notify (self, base = "", descr = "", icon = "", urgency = None):
        if self._mq is None:
            self.do_notify(base, descr, icon, urgency)
        else:
            string = "\0".join(["notify", base, descr, icon])

            if urgency is not None:
                string += "\0%d" % urgency
            else:
                string += "\0"

            self.__send(string)

    def send_cmd (self, cmdlist):
        if self._mq is None:
            self.do_cmd(cmdlist)
        else:
            self.__send("\0".join(["cmd"] +cmdlist))

    def close (self):
        if self._mq is not None:
            self.__send("close")
