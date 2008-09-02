# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/mailinfo.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import smtplib, socket
import time

from .basic import AbstractDialog
from ..utils import GtkThread
from ..dialogs import mail_failure_dialog
from ...helper import debug, info
from ...constants import VERSION

class MailInfoWindow (AbstractDialog):
    TO = "bugs@portato.necoro.net"

    def __init__ (self, parent, tb):

        AbstractDialog.__init__(self, parent)
        
        self.tb = tb
        self.window.show_all()

    def set_data (self):
        name = self.tree.get_widget("nameEntry").get_text()
        addr = self.tree.get_widget("mailEntry").get_text()

        if not addr:
            addr = self.TO

        if name:
            fro = "%s <%s>" % (name, addr)
        else:
            fro = addr

        commentBuffer = self.tree.get_widget("commentEntry").get_buffer()
        text = commentBuffer.get_text(*commentBuffer.get_bounds())

        if text:
            text += "\n\n===========\n"

        text += self.tb

        message = """From: %s
To: %s
Subject: %s
%s""" % ( fro, self.TO, ("[Bug Report] Bug in Portato %s" % VERSION), text)

        self.addr = addr
        self.message = message

    def send (self):
        try:
            debug("Connecting to server")
            server = smtplib.SMTP("mail.necoro.eu")
            debug("Sending mail")
            try:
                try:
                    server.sendmail(self.addr, self.TO, self.message)
                except smtplib.SMTPRecipientsRefused, e:
                    info(_("An error occurred while sending. I think we were greylisted. The error: %s") % e)
                    info(_("Retrying after waiting 60 seconds."))
                    time.sleep(60)
                    server.sendmail(self.addr, self.TO, self.message)
                debug("Sent")
            finally:
                server.quit()
        except socket.error, e:
            mail_failure_dialog("%s (Code: %s)" % (e.args[1], e.args[0]))
        
    def cb_cancel_clicked (self, *args):

        self.close()
        return True

    def cb_send_clicked (self, *args):
        self.set_data()
        GtkThread(target = self.send, name = "Mail Send Thread").start()
        self.close()
        return True
