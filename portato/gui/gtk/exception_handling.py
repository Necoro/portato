# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/exception_handling.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
#
# Written by René 'Necoro' Neumann

from __future__ import absolute_import, with_statement

import gtk, pango, gobject
import sys, traceback

from threading import Thread
from gettext import lgettext as _
from StringIO import StringIO

from ...helper import debug, error
from .dialogs import file_chooser_dialog, io_ex_dialog

class GtkThread (Thread):
	def run(self):
		try:
			Thread.run(self)
		except SystemExit:
			raise # let normal thread handle it
		except:
			type, val, tb = sys.exc_info()
			try:
				sys.excepthook(type, val, tb, thread = self.getName())
			except TypeError:
				raise type, val, tb # let normal thread handle it
			finally:
				del type, val, tb

class UncaughtExceptionDialog(gtk.MessageDialog):
	"""Original idea by Gustavo Carneiro - original code: http://www.daa.com.au/pipermail/pygtk/attachments/20030828/2d304204/gtkexcepthook.py."""

	def __init__(self, type, value, tb, thread = None):

		super(UncaughtExceptionDialog,self).__init__(parent=None, flags=0,  type=gtk.MESSAGE_WARNING, buttons=gtk.BUTTONS_NONE, message_format=_("A programming error has been detected during the execution of this program."))
		self.set_title(_("Bug Detected"))
		self.format_secondary_text(_("It probably isn't fatal, but should be reported to the developers nonetheless."))

		self.add_button(_("Show Details"), 1)
		self.add_button(gtk.STOCK_SAVE_AS, 2)
		self.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)

		# Details
		self.textview = gtk.TextView()
		self.textview.set_editable(False)
		self.textview.modify_font(pango.FontDescription("Monospace"))
	
		self.sw = gtk.ScrolledWindow();
		self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.sw.add(self.textview)
	
		self.tbFrame = gtk.Frame()
		self.tbFrame.set_shadow_type(gtk.SHADOW_IN)
		self.tbFrame.add(self.sw)
		self.tbFrame.set_border_width(6)
		
		self.vbox.add(self.tbFrame)
		
		textbuffer = self.textview.get_buffer()
		self.text = get_trace(type, value, tb)
		if thread:
			self.text = _("Exception in thread \"%(thread)s\":\n%(trace)s") % {"thread": thread, "trace": text}
		textbuffer.set_text(self.text)
		self.textview.set_size_request(gtk.gdk.screen_width()/2, gtk.gdk.screen_height()/3)

		self.details = self.tbFrame
		self.set_position(gtk.WIN_POS_CENTER)
		self.set_gravity(gtk.gdk.GRAVITY_CENTER)

	def run (self):
		while True:
			resp = super(UncaughtExceptionDialog, self).run()
			if resp == 1:
				self.details.show_all()
				self.set_response_sensitive(1, False)
			elif resp == 2:
				debug("Want to save")
				file = file_chooser_dialog(_("Save traceback..."), self)
				if file:
					debug("Save to %s", file)
					
					try:
						with open(file, "w") as f:
							f.writelines(self.text)
					except IOError, e:
						io_ex_dialog(e)

				else:
					debug("Nothing to save")
			else:
				break
		self.destroy()

def get_trace(type, value, tb):
	trace = StringIO()
	traceback.print_exception(type, value, tb, None, trace)
	traceStr = trace.getvalue()
	trace.close()
	return traceStr
	
def register_ex_handler():
	
	def handler(type, val, tb, thread = None):
		def run_dialog():
			UncaughtExceptionDialog(type, val, tb, thread).run()
		
		if thread:
			error(_("Exception in thread \"%(thread)s\":\n%(trace)s"), {"thread": thread, "trace": get_trace(type, val, tb)})
		else:
			error(_("Exception:\n%s"), get_trace(type, val, tb))
		
		gobject.idle_add(run_dialog)

	sys.excepthook = handler
