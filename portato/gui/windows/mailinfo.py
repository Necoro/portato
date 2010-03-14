# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/mailinfo.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import smtplib, socket
import time
import gtk, pango
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import basename

from .basic import AbstractDialog
from ..utils import GtkThread
from ..dialogs import mail_failure_dialog
from ...helper import debug, info
from ...constants import VERSION, CONFIG_LOCATION
from ...log import LOGFILE
from ... import session

class ShowDialog (gtk.Dialog):

    def __init__(self, parent, f):
        gtk.Dialog.__init__(self, f, parent, buttons = (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        textview = gtk.TextView()
        textview.set_editable(False)
        textview.modify_font(pango.FontDescription("Monospace"))
        textview.set_size_request(gtk.gdk.screen_width()/2, gtk.gdk.screen_height()/3)
    
        sw = gtk.ScrolledWindow();
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(textview)
        
        self.vbox.add(sw)

        textbuffer = textview.get_buffer()

        with open(f) as text:
            textbuffer.set_text(text.read())

        self.vbox.show_all()

class MailInfoWindow (AbstractDialog):
    TO = "bugs@portato.necoro.net"

    def __init__ (self, parent, tb):

        AbstractDialog.__init__(self, parent)

        self.files = [LOGFILE, CONFIG_LOCATION] + [s._file for s in session.sessionlist]
        self.fileList = self.tree.get_widget("fileList")
        self.build_file_list()
        
        self.tb = tb
        self.window.show_all()

    def build_file_list(self):
        store = gtk.ListStore(bool, str)

        for f in self.files:
            store.append((True, f))

        self.fileList.set_model(store)
        cell = gtk.CellRendererText()
        tCell = gtk.CellRendererToggle()
        tCell.set_property("activatable", True)
        tCell.connect("toggled", self.cb_file_toggled)

        self.fileList.append_column(gtk.TreeViewColumn(None, tCell, active = 0))
        self.fileList.append_column(gtk.TreeViewColumn(None, cell, text = 1))

    def cb_file_toggled(self, cell, path):
        store = self.fileList.get_model()
        store[path][0] = not store[path][0]
        return True

    def cb_file_clicked(self, view, path, *args):
        store = view.get_model()
        f = store[path][1]
        
        dialog = ShowDialog(self.window, f)
        dialog.run()
        dialog.destroy()

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

        # logs
        for (active, f) in self.fileList.get_model():
            if active:
                debug("Attaching '%s'", f)
                with open(f, "r") as text:
                    log = MIMEText(text.read(), "plain", "utf-8")
                    log.add_header('Content-Disposition', 'attachment', filename=basename(f))

                self.message.attach(log)

    def send (self):
        try:
            debug("Connecting to server")
            server = smtplib.SMTP("mail.necoro.eu")
            debug("Sending mail")
            try:
                for i in range(5): # try 5 times at max
                    try:
                        server.sendmail(self.addr, self.TO, self.message.as_string())
                    except smtplib.SMTPRecipientsRefused, e:
                        info(_("An error occurred while sending. I think we were greylisted. The error: %s") % e)
                        info(_("Retrying after waiting %d seconds."), 30)
                        time.sleep(30)
                    else:
                        debug("Sent")
                        break
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
