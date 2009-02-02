# -*- coding: utf-8 -*-
#
# File: portato/gui/dialogs.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import gtk
from ..helper import error

def mail_failure_dialog(e):
    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("Mail could not be sent"))
    dialog.format_secondary_text(_("The error was: %s") % e)
    ret = dialog.run()
    dialog.destroy()
    return ret

def queue_not_empty_dialog():
    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_NONE, _("Do you really want to quit?"))
    dialog.format_secondary_text(_("There are some packages in the emerge queue and/or an emerge process is running."))
    dialog.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
    ret = dialog.run()
    dialog.destroy()
    return ret

def io_ex_dialog (io_ex):
    string = io_ex.strerror
    if io_ex.filename:
        string = string+": "+io_ex.filename
    
    error(string)
    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, string)
    ret = dialog.run()
    dialog.destroy()
    return ret

def blocked_dialog (blocked, blocks):
    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("%(blocked)s is blocked by %(blocks)s.") % {"blocked":blocked, "blocks" : blocks})
    dialog.format_secondary_text(_("Please unmerge the blocking package."))
    ret = dialog.run()
    dialog.destroy()
    return ret

def not_root_dialog ():
    errorMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("You are not root."))
    ret = errorMB.run()
    errorMB.destroy()
    return ret

def unmask_dialog (cpv):
    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, _("%s seems to be masked.") % cpv )
    dialog.format_secondary_text(_("Do you want to unmask it and its dependencies?"))
    ret = dialog.run()
    dialog.destroy()
    return ret

def nothing_found_dialog ():
    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, _("Package not found!"))
    ret = dialog.run()
    dialog.destroy()
    return ret

def changed_flags_dialog (what = "flags"):
    check = gtk.CheckButton(_("Do not show this dialog again."))
    hintMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, _("Changed %s") % what)
    hintMB.format_secondary_text(_("Portato will write these changes into the appropriate files.\nPlease backup them if you think it is necessairy."))
    hintMB.vbox.add(check)
    hintMB.vbox.show_all()
    ret = hintMB.run()
    hintMB.destroy()

    return ret, check.get_active()

def remove_deps_dialog ():
    infoMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, _("You cannot remove dependencies. :)"))
    ret = infoMB.run()
    infoMB.destroy()
    return ret

def remove_updates_dialog():
    askMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, _("This is the updates queue. You cannot remove single elements.\nDo you want to clear the whole queue instead?"))
    ret = askMB.run()
    askMB.destroy()
    return ret

def remove_queue_dialog ():
    askMB = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, _("Do you really want to clear the whole queue?"))
    ret = askMB.run()
    askMB.destroy()
    return ret

def file_chooser_dialog (title, parent):
    fc = gtk.FileChooserDialog(title = title, parent = parent, action = gtk.FILE_CHOOSER_ACTION_SAVE, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
    fc.set_do_overwrite_confirmation(True)
    ret = fc.run()

    if ret == gtk.RESPONSE_ACCEPT:
        ret = fc.get_filename()
    else:
        ret = None

    fc.destroy()
    return ret

def prereq_error_dialog (e):
    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("A prerequisite for starting Portato was not matched."))
    dialog.format_secondary_text(e.message)
    ret = dialog.run()
    dialog.destroy()
    return ret

def no_versions_dialog (cp):
    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK, _("No versions of package '%s' found!") % cp)
    ret = dialog.run()
    dialog.destroy()
    return ret

