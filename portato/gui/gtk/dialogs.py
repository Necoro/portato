# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/dialogs.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import gtk
from gettext import lgettext as _

def queue_not_empty_dialog():
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, _("There are some packages in the emerge queue and/or an emerge process is running.\nDo you really want to quit?"))
	ret = dialog.run()
	dialog.destroy()
	return ret

def io_ex_dialog (io_ex):
	string = io_ex.strerror
	if io_ex.filename:
		string = string+": "+io_ex.filename
	
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, string)
	ret = dialog.run()
	dialog.destroy()
	return ret

def blocked_dialog (blocked, blocks):
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("%(blocked)s is blocked by %(blocks)s.\nPlease unmerge the blocking package.") % {"blocked":blocked, "blocks" : blocks})
	ret = dialog.run()
	dialog.destroy()
	return ret

def not_root_dialog ():
	errorMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "_(You are not root."))
	ret = errorMB.run()
	errorMB.destroy()
	return ret

def unmask_dialog (cpv):
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, _("%s seems to be masked.\nDo you want to unmask it and its dependencies?") % cpv)
	ret = dialog.run()
	dialog.destroy()
	return ret

def nothing_found_dialog ():
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, _("Package not found!"))
	ret = dialog.run()
	dialog.destroy()
	return ret

def changed_flags_dialog (what = "flags"):
	hintMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK,
						_("You have changed %s. Portato will write these changes into the appropriate files. Please backup them if you think it is necessairy.") % what)
	ret = hintMB.run()
	hintMB.destroy()
	return ret

def remove_deps_dialog ():
	infoMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, _("You cannot remove dependencies. :)"))
	ret = infoMB.run()
	infoMB.destroy()
	return ret

def remove_queue_dialog ():
	askMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, _("Do you really want to clear the whole queue?"))
	ret = askMB.run()
	askMB.destroy()
	return ret
