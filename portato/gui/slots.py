# -*- coding: utf-8 -*-
#
# File: portato/gui/slots.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import gtk
from ..plugin import WidgetSlot # other modules might import WidgetSlot from here

class PluginMenuSlot (WidgetSlot):

    def __init__ (self, tree):
        WidgetSlot.__init__(self, self.create_action, "Plugin Menu")
        
        self.ctr = 0 # counter for the plugin actions
        self.uim = tree.get_widget("uimanager")
        self.ag = tree.get_widget("pluginActionGroup")

    def create_action (self, label):
        aname = "plugin%d" % self.ctr
        a = gtk.Action(aname, label, None, None)
        self.ctr += 1
        
        return a

    def add (self, widget):
        action = widget.widget
        self.ag.add_action(action)

        # add to UI
        mid = self.uim.new_merge_id()
        self.uim.add_ui(mid, "ui/menubar/pluginMenu", action.get_name(), action.get_name(), gtk.UI_MANAGER_MENUITEM, False)

        self.uim.ensure_update()

class NotebookSlot (WidgetSlot):

    def __init__ (self, notebook, *args, **kwargs):
        self.notebook = notebook

        WidgetSlot.__init__(self, *args, **kwargs)

    def add (self, widget):
        if isinstance(widget.widget, tuple):
            label = gtk.Label(widget.widget[1])
        else:
            label = None
        
        widget = widget.widget[0]

        self.notebook.append_page(widget, label)
