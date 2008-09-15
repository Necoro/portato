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

from __future__ import absolute_import, with_statement

import smtplib, socket
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .basic import AbstractDialog
from ..utils import GtkThread
from ..dialogs import mail_failure_dialog
from ...helper import debug, info
from ...constants import VERSION
from ...log import LOGFILE

class MailInfoWindow (AbstractDialog):
    TO = "bugs@portato.necoro.net"

    def __init__ (self, parent, tb):

        AbstractDialog.__init__(self, parent)
        
        self.tb = tb
        self.window.show_all()

    def set_data (self):
        self.message = MIMEMultipart()
        self.message["Subject"] = "[Bug Report] Bug in Portato %s" % VERSION
        self.message["To"] = self.TO
        
        # TO and FROM        
        name = self.tree.get_widget("nameEntry").get_text()
        self.addr = self.tree.get_widget("mailEntry").get_text()

        if not self.addr:
            self.addr = self.TO

        if name:
            self.message["From"] = "%s <%s>" % (name, self.addr)
        else:
            self.message["From"] = self.addr

        # text
        commentBuffer = self.tree.get_widget("commentEntry").get_buffer()
        text = commentBuffer.get_text(*commentBuffer.get_bounds())

        if text:
            text += "\n\n===========\n"

        text += self.tb

        txtmsg = MIMEText(text, "plain", "utf-8")
        self.message.attach(txtmsg)

        # log
        if self.tree.get_widget("logCheck").get_active():
            with open(LOGFILE, "r") as f:
                log = MIMEText(f.read(), "plain", "utf-8")
                log.add_header('Content-Disposition', 'attachment', filename='portato.log')

            self.message.attach(log)

    def send (self):
        try:
            debug("Connecting to server")
            server = smtplib.SMTP("mail.necoro.eu")
            debug("Sending mail")
            try:
                try:
                    server.sendmail(self.addr, self.TO, self.message.as_string())
                except smtplib.SMTPRecipientsRefused, e:
                    info(_("An error occurred while sending. I think we were greylisted. The error: %s") % e)
                    info(_("Retrying after waiting 60 seconds."))
                    time.sleep(60)
                    server.sendmail(self.addr, self.TO, self.message.as_string())
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
