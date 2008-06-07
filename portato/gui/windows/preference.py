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

from .basic import AbstractDialog
from ..dialogs import io_ex_dialog
from ...helper import debug

class PreferenceWindow (AbstractDialog):
	"""Window displaying some preferences."""
	
	# all checkboxes in the window
	# widget name -> option name
	checkboxes = {
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

	def __init__ (self, parent, cfg, console_fn, linkbtn_fn, tabpos_fn):
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
		@type tabpos_fn: function(gtk.ComboBox,int)"""
		
		AbstractDialog.__init__(self, parent)

		# our config
		self.cfg = cfg

		# the setter functions
		self.console_fn = console_fn
		self.linkbtn_fn = linkbtn_fn
		self.tabpos_fn = tabpos_fn
		
		# set the bg-color of the hint
		hintEB = self.tree.get_widget("hintEB")
		hintEB.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#f3f785"))

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

		font = self.consoleFontBtn.get_font_name()
		self.cfg.set("consolefont", font, section = "GUI")
		self.console_fn(font)

		self.cfg.set("titlelength", self.titleLengthSpinBtn.get_value(), section = "GUI")

		pkgPos = self.pkgTabCombo.get_active()+1
		sysPos = self.systemTabCombo.get_active()+1

		self.cfg.set("packageTabPos", str(pkgPos), section = "GUI")
		self.cfg.set("systemTabPos", str(sysPos), section = "GUI")

		self.tabpos_fn(map(self.tabpos.get, (pkgPos, sysPos)))
		
		self.linkbtn_fn(self.cfg.get("browserCmd", section="GUI"))

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
