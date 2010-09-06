# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/preference.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from future_builtins import map, filter, zip

import gtk

from ...backend import system

from .basic import AbstractDialog
from ..dialogs import io_ex_dialog
from ..utils import get_color
from ...helper import debug
from ... import db

class PreferenceWindow (AbstractDialog):
    """Window displaying some preferences."""
    
    # all checkboxes in the window
    # widget name -> option name
    checkboxes = {
            "collapseCatCheck"        : ("collapseCats", "GUI"),
            "consoleUpdateCheck"    : ("updateConsole", "GUI"),
            "debugCheck"            : "debug",
            "deepCheck"                : "deep",
            "newUseCheck"            : "newuse",
            "maskPerVersionCheck"    : "maskPerVersion",
            "minimizeCheck"            : ("hideOnMinimize", "GUI"),
            "searchOnTypeCheck"        : ("searchOnType", "GUI"),
            "showSlotsCheck"        : ("showSlots", "GUI"),
            "systrayCheck"            : ("showSystray", "GUI"),
            "testPerVersionCheck"    : "keywordPerVersion",
            "titleUpdateCheck"        : ("updateTitle", "GUI"),
            "usePerVersionCheck"    : "usePerVersion"
            }
    
    # all edits in the window
    # widget name -> option name
    edits = {
            "maskFileEdit"        : "maskFile",
            "testFileEdit"        : "keywordFile",
            "useFileEdit"        : "useFile",
            "syncCommandEdit"    : "syncCommand",
            "browserEdit"        : ("browserCmd", "GUI")
            }

    # the mappings for the tabpos combos
    tabpos = {
            1 : gtk.POS_TOP,
            2 : gtk.POS_BOTTOM,
            3 : gtk.POS_LEFT,
            4 : gtk.POS_RIGHT
            }

    def __init__ (self, parent, cfg, console_fn, linkbtn_fn, tabpos_fn, catmodel_fn, labelcolor_fn):
        """Constructor.

        @param parent: parent window
        @type parent: gtk.Window
        @param cfg: configuration object
        @type cfg: gui_helper.Config
        @param console_fn: function to call to set the console font
        @type console_fn: function(string)
        @param linkbtn_fn: function to call to set the linkbutton behavior
        @type linkbtn_fn: function(string)
        @param tabpos_fn: function to call to set the tabposition of the notebooks
        @type tabpos_fn: function(gtk.ComboBox,int)
        @param catmodel_fn: function to call to set the model of the cat list (collapsed/not collapsed)
        @type catmodel_fn: function()
        @param labelcolor_fn: function to call to set the color of the label
        @type labelcolor_fn: function(gtk.gdk.Color)"""
        
        AbstractDialog.__init__(self, parent)

        # our config
        self.cfg = cfg

        # the size
        height = self.cfg.get_session("prefheight", "GUI")
        if height is None:
            height = int(gtk.gdk.screen_height() * 0.8) # see 4/5 * screen_height as maximum
        else:
            height = int(height)

        width = self.cfg.get_session("prefwidth", "GUI")
        if width is None:
            width = -1 # default
        else:
            width = int(width)

        self.window.resize(width, height)

        # the setter functions
        self.console_fn = console_fn
        self.linkbtn_fn = linkbtn_fn
        self.tabpos_fn = tabpos_fn
        self.catmodel_fn = catmodel_fn
        self.labelcolor_fn = labelcolor_fn
        
        # set the bg-color of the hint
        hintEB = self.tree.get_widget("hintEB")
        hintEB.modify_bg(gtk.STATE_NORMAL, get_color(self.cfg, "prefhint"))

        # the checkboxes
        for box, val in self.checkboxes.items():
            if isinstance(val, tuple):
                self.tree.get_widget(box).set_active(self.cfg.get_boolean(val[0], section = val[1]))
            else:
                self.tree.get_widget(box).set_active(self.cfg.get_boolean(val))

        # the edits
        for edit, val in self.edits.items():
            if isinstance(val,tuple):
                self.tree.get_widget(edit).set_text(self.cfg.get(val[0], section = val[1]))
            else:
                self.tree.get_widget(edit).set_text(self.cfg.get(val))

        # the set list
        self.setList = self.tree.get_widget("setList")
        if system.has_set_support():
            self.fill_setlist()
            self.tree.get_widget("setFrame").show()

        # the console font button
        self.consoleFontBtn = self.tree.get_widget("consoleFontBtn")
        self.consoleFontBtn.set_font_name(self.cfg.get("consolefont", section = "GUI"))

        # the console title length spin button
        self.titleLengthSpinBtn = self.tree.get_widget("titleLengthSpinBtn")
        self.titleLengthSpinBtn.set_value(int(self.cfg.get("titlelength", section = "GUI")))

        # the color buttons
        self.pkgTableColorBtn = self.tree.get_widget("pkgTableColorBtn")
        self.pkgTableColorBtn.set_color(get_color(self.cfg, "packagetable"))

        self.prefColorBtn = self.tree.get_widget("prefColorBtn")
        self.prefColorBtn.set_color(get_color(self.cfg, "prefhint"))

        # the comboboxes
        self.systemTabCombo = self.tree.get_widget("systemTabCombo")
        self.pkgTabCombo = self.tree.get_widget("packageTabCombo")

        for c in (self.systemTabCombo, self.pkgTabCombo):
            model = gtk.ListStore(str)
            for i in (_("Top"), _("Bottom"), _("Left"), _("Right")):
                model.append((i,))

            c.set_model(model)
            
            cell = gtk.CellRendererText()
            c.pack_start(cell)
            c.set_attributes(cell, text = 0)

        self.systemTabCombo.set_active(int(self.cfg.get("systemTabPos", section = "GUI"))-1)
        self.pkgTabCombo.set_active(int(self.cfg.get("packageTabPos", section = "GUI"))-1)

        # the database combo
        dbtype = self.cfg.get("type", section = "DATABASE")
        self.databaseCombo = self.tree.get_widget("databaseCombo")
        model = gtk.ListStore(str, str, str)

        active = 0
        for ctr, (key, t) in enumerate(db.types.iteritems()):
            if key == dbtype:
                active = ctr

            model.append([t.name, t.descr, key])

        self.databaseCombo.set_model(model)
        self.databaseCombo.set_active(active)
        
        cell = gtk.CellRendererText()
        self.databaseCombo.pack_start(cell)
        self.databaseCombo.set_attributes(cell, text = 0)

        self.cb_db_combo_changed()

        self.window.show_all()

    def _save(self):
        """Sets all options in the Config-instance."""
        
        for box, val in self.checkboxes.items():
            if isinstance(val, tuple):
                self.cfg.set(val[0], self.tree.get_widget(box).get_active(), section = val[1])
            else:
                self.cfg.set(val, self.tree.get_widget(box).get_active())

        for edit, val in self.edits.items():
            if isinstance(val,tuple):
                self.cfg.set(val[0], self.tree.get_widget(edit).get_text(), section = val[1])
            else:
                self.cfg.set(val,self.tree.get_widget(edit).get_text())

        if system.has_set_support():
            self.cfg.set("updatesets", ", ".join(sorted(name for enabled, markup, descr, name in self.setList.get_model() if enabled)))

        font = self.consoleFontBtn.get_font_name()
        self.cfg.set("consolefont", font, section = "GUI")
        self.console_fn(font)

        self.cfg.set("titlelength", str(self.titleLengthSpinBtn.get_value_as_int()), section = "GUI")

        pkgPos = self.pkgTabCombo.get_active()+1
        sysPos = self.systemTabCombo.get_active()+1

        self.cfg.set("packageTabPos", str(pkgPos), section = "GUI")
        self.cfg.set("systemTabPos", str(sysPos), section = "GUI")

        self.tabpos_fn(list(map(self.tabpos.get, (pkgPos, sysPos))))
        
        self.linkbtn_fn(self.cfg.get("browserCmd", section="GUI"))

        self.catmodel_fn()

        # colors
        c = self.pkgTableColorBtn.get_color()
        self.cfg.set("packagetable", str(c)[1:], section = "COLORS")
        self.labelcolor_fn(c)

        c = self.prefColorBtn.get_color()
        self.cfg.set("prefhint", str(c)[1:], section = "COLORS")

        # DB type
        m = self.databaseCombo.get_model()
        a = self.databaseCombo.get_active()
        self.cfg.set("type", m[a][2], section = "DATABASE")

    def fill_setlist (self):
        store = gtk.ListStore(bool, str, str, str)

        enabled = [x.strip() for x in self.cfg.get("updatesets").split(",")]
        
        for set, descr in system.get_sets(description = True):
            store.append([set in enabled, "<i>%s</i>" % set, descr, set])

        tCell = gtk.CellRendererToggle()
        tCell.set_property("activatable", True)
        tCell.connect("toggled", self.cb_check_toggled) # emulate the normal toggle behavior ...

        sCell = gtk.CellRendererText()

        col = gtk.TreeViewColumn(_("Package Set"), tCell, active = 0)
        col.pack_start(sCell)
        col.add_attribute(sCell, "markup",  1)
        self.setList.append_column(col)

        self.setList.append_column(gtk.TreeViewColumn(_("Description"), sCell, text = 2))

        self.setList.set_model(store)

    def cb_db_combo_changed (self, *args):
        model = self.databaseCombo.get_model()
        active = self.databaseCombo.get_active()

        descr = self.tree.get_widget("dbDescriptionLabel")
        descr.set_markup("<i>%s</i>" % model[active][1])
    
    def cb_ok_clicked(self, button):
        """Saves, writes to config-file and closes the window."""
        self._save()
        try:
            self.cfg.write()
        except IOError as e:
            io_ex_dialog(e)

        self.window.destroy()

    def cb_cancel_clicked (self, button):
        """Just closes - w/o saving."""
        self.window.destroy()

    def cb_check_toggled (self, cell, path):
        # for whatever reason we have to define normal toggle behavior explicitly
        store = self.setList.get_model()
        store[path][0] = not store[path][0]
        return True

    def cb_size_changed (self, widget, event, *args):
        self.cfg.set_session("prefheight", "GUI", event.height)
        self.cfg.set_session("prefwidth", "GUI", event.width)
