# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/preference.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import gtk

from ...backend import system

from .basic import AbstractDialog
from ..dialogs import io_ex_dialog
from ..utils import get_color
from ...helper import debug

class PreferenceWindow (AbstractDialog):
	"""Window displaying some preferences."""
	
	# all checkboxes in the window
	# widget name -> option name
	checkboxes = {
			"collapseCatCheck"		: ("collapseCats", "GUI"),
			"consoleUpdateCheck"	: ("updateConsole", "GUI"),
			"debugCheck"			: "debug",
			"deepCheck"				: "deep",
			"newUseCheck"			: "newuse",
			"maskPerVersionCheck"	: "maskPerVersion",
			"minimizeCheck"			: ("hideOnMinimize", "GUI"),
			"searchOnTypeCheck"		: ("searchOnType", "GUI"),
			"showSlotsCheck"		: ("showSlots", "GUI"),
			"systrayCheck"			: ("showSystray", "GUI"),
			"testPerVersionCheck"	: "keywordPerVersion",
			"titleUpdateCheck"		: ("updateTitle", "GUI"),
			"usePerVersionCheck"	: "usePerVersion"
			}
	
	# all edits in the window
	# widget name -> option name
	edits = {
			"maskFileEdit"		: "maskFile",
			"testFileEdit"		: "keywordFile",
			"useFileEdit"		: "useFile",
			"syncCommandEdit"	: "syncCommand",
			"browserEdit"		: ("browserCmd", "GUI")
			}

	# the mappings for the tabpos combos
	tabpos = {
			1 : gtk.POS_TOP,
			2 : gtk.POS_BOTTOM,
			3 : gtk.POS_LEFT,
			4 : gtk.POS_RIGHT
			}

	def __init__ (self, parent, cfg, console_fn, linkbtn_fn, tabpos_fn, catmodel_fn):
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
		@type catmodel_fn: function()"""
		
		AbstractDialog.__init__(self, parent)

		# our config
		self.cfg = cfg

		# the setter functions
		self.console_fn = console_fn
		self.linkbtn_fn = linkbtn_fn
		self.tabpos_fn = tabpos_fn
		self.catmodel_fn = catmodel_fn
		
		# set the bg-color of the hint
		hintEB = self.tree.get_widget("hintEB")
		hintEB.modify_bg(gtk.STATE_NORMAL, get_color(self.cfg, "prefhint"))

		# the checkboxes
		for box, val in self.checkboxes.iteritems():
			if isinstance(val, tuple):
				self.tree.get_widget(box).\
						set_active(self.cfg.get_boolean(val[0], section = val[1]))
			else:
				self.tree.get_widget(box).\
						set_active(self.cfg.get_boolean(val))

		# the edits
		for edit, val in self.edits.iteritems():
			if isinstance(val,tuple):
				self.tree.get_widget(edit).\
						set_text(self.cfg.get(val[0], section = val[1]))
			else:
				self.tree.get_widget(edit).\
					set_text(self.cfg.get(val))

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

		# the comboboxes
		self.systemTabCombo = self.tree.get_widget("systemTabCombo")
		self.pkgTabCombo = self.tree.get_widget("packageTabCombo")

		for c in (self.systemTabCombo, self.pkgTabCombo):
			m = c.get_model()
			m.clear()
			for i in (_("Top"), _("Bottom"), _("Left"), _("Right")):
				m.append((i,))

		self.systemTabCombo.set_active(int(self.cfg.get("systemTabPos", section = "GUI"))-1)
		self.pkgTabCombo.set_active(int(self.cfg.get("packageTabPos", section = "GUI"))-1)

		self.window.show_all()

	def _save(self):
		"""Sets all options in the Config-instance."""
		
		for box, val in self.checkboxes.iteritems():
			if isinstance(val, tuple):
				self.cfg.set_boolean(val[0], self.tree.get_widget(box).get_active(), section = val[1])
			else:
				self.cfg.set_boolean(val, self.tree.get_widget(box).get_active())

		for edit, val in self.edits.iteritems():
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

		self.tabpos_fn(map(self.tabpos.get, (pkgPos, sysPos)))
		
		self.linkbtn_fn(self.cfg.get("browserCmd", section="GUI"))

		self.catmodel_fn()

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

	def cb_ok_clicked(self, button):
		"""Saves, writes to config-file and closes the window."""
		self._save()
		try:
			self.cfg.write()
		except IOError, e:
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
