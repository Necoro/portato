# -*- coding: utf-8 -*-
#
# File: geneticone/gui/gtk/dialogs.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import gtk

def blocked_dialog (blocked, blocks):
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, blocked+" is blocked by "+blocks+".\nPlease unmerge the blocking package.")
	dialog.run()
	dialog.destroy()

def not_root_dialog ():
	errorMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "You cannot (un)merge without being root.")
	errorMB.run()
	errorMB.destroy()

def masked_dialog (cpv):
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, cpv+" seems to be masked.\nPlease edit the appropriate file(s) to unmask it and restart Genetic/One.\n")
	dialog.run()
	dialog.destroy()

def unmask_dialog (cpv):
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, cpv+" seems to be masked.\nDo you want to unmask it and its dependencies?.\n")
	ret = dialog.run()
	dialog.destroy()
	return ret

def nothing_found_dialog ():
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "Package not found!")
	dialog.run()
	dialog.destroy()

def changed_flags_dialog (what = "flags"):
	hintMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK,
						"You have changed %s. Genetic/One will write these changes into the appropriate files. Please backup them if you think it is necessairy." % what)
	hintMB.run()
	hintMB.destroy()

def remove_deps_dialog ():
	infoMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "You cannot remove dependencies. :)")
	infoMB.run()
	infoMB.destroy()

def remove_queue_dialog ():
	askMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you really want to clear the whole queue?")
	ret = askMB.run()
	askMB.destroy()
	return ret
