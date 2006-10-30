# -*- coding: utf-8 -*-
#
# File: geneticone/gui/gtk/windows.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

VERSION = "0.4.6-svn"
CONFIG_LOCATION = "/etc/geneticone/geneticone.cfg"

# gtk stuff
import pygtk
pygtk.require("2.0")
import gtk
import gobject

#our backend stuff
from geneticone.helper import *
from geneticone import backend
from geneticone.backend import flags
from geneticone.backend.exceptions import *

# more GUI stuff
from geneticone.gui.gui_helper import Database, Config, EmergeQueue
from dialogs import *
from wrapper import GtkTree, GtkConsole

# for the terminal
import vte

# other
from portage_util import unique_array

class AbstractDialog:
	"""A class all our dialogs get derived from. It sets useful default vars and automatically handles the ESC-Button."""

	def __init__ (self, parent, title):
		"""Constructor.

		@param parent: the parent window
		@type parent: gtk.Window
		@param title: the title of the window
		@type title: string"""

		# create new
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		
		# set title
		self.window.set_title(title)
		
		# set modal and transient for the parent --> you have to close this one to get back to the parent
		self.window.set_modal(True)
		self.window.set_transient_for(parent)
		self.window.set_destroy_with_parent(True)

		# not resizable
		self.window.set_resizable(False)
		
		# default size = (1,1) ==> as small as possible
		self.window.set_default_size(1,1)

		# catch the ESC-key
		self.window.connect("key-press-event", self.cb_key_pressed)

	def cb_key_pressed (self, widget, event):
		"""Closes the window if ESC is pressed."""
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == "Escape":
			self.window.destroy()
			return True
		else:
			return False

class AboutWindow (AbstractDialog):
	"""A window showing the "about"-informations."""

	def __init__ (self, parent):
		"""Constructor.

		@param parent: the parent window
		@type parent: gtk.Window"""

		AbstractDialog.__init__(self, parent, "About Genetic/One")
		
		box = gtk.VBox(False)
		self.window.add(box)
		
		# about label
		label = gtk.Label()
		label.set_justify(gtk.JUSTIFY_CENTER)
		label.set_markup("""
<big><b>Genetic/One v.%s</b></big>
A Portage-GUI
		
This software is licensed under the terms of the GPLv2.
Copyright (C) 2006 René 'Necoro' Neumann &lt;necoro@necoro.net&gt;

<small>Thanks to Fred for support and ideas :P</small>
""" % VERSION)
		box.pack_start(label)

		# button
		okBtn = gtk.Button("OK")
		okBtn.connect("clicked", lambda x: self.window.destroy())
		box.pack_start(okBtn)

		# finished -> show
		self.window.show_all()

class SearchWindow (AbstractDialog):
	"""A window showing the results of a search process."""
	
	def __init__ (self, parent, list, jump_to):
		"""Constructor.

		@param parent: parent-window
		@type parent: gtk.Window
		@param list: list of results to show
		@type list: string[]
		@param jump_to: function to call if "OK"-Button is hit
		@type jump_to: function(string)"""
		
		AbstractDialog.__init__(self, parent, "Search results")
		
		self.list = list # list to show
		self.jump_to = jump_to # function to call for jumping

		box = gtk.HBox(False)
		self.window.add(box)

		# combo box
		self.combo = gtk.combo_box_new_text()
		for x in list:
			self.combo.append_text(x)
		self.combo.set_active(0) # first item
		self.combo.connect("key-press-event", self.cb_key_pressed_combo)

		box.pack_start(self.combo)

		# ok-button
		okBtn = gtk.Button("OK")
		okBtn.connect("clicked", self.cb_ok_btn_clicked)
		box.pack_start(okBtn)

		# finished --> show
		self.window.show_all()

	def cb_ok_btn_clicked (self, button):
		"""Called if the OK-Button is clicked. 
		Calls self.jump_to(selected_entry) and closes the window."""
		self.window.destroy()
		self.jump_to(self.list[self.combo.get_active()])
		return True

	def cb_key_pressed_combo (self, widget, event):
		"""Emulates a ok-button-click."""
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == "Return": # take it as an "OK" if Enter is pressed
			self.cb_ok_btn_clicked(widget)
			return True
		else:
			return False

class PreferenceWindow (AbstractDialog):
	"""Window displaying some preferences."""

	def __init__ (self, parent, cfg):
		"""Constructor.

		@param parent: parent window
		@type parent: gtk.Window
		@param cfg: configuration object
		@type cfg: gui_helper.Config"""

		AbstractDialog.__init__(self, parent, "Preferences")
		self.window.set_resizable(True) # override the default of the AbstractDialog
		
		# our config
		self.cfg = cfg
		
		box = gtk.VBox()
		box.set_spacing(5)

		self.window.add(box)

		# En-/Disable Debugging
		self.debugCb = self.draw_cb(box, "Debugging modus", "debug_opt")

		# --deep
		self.deepCb = self.draw_cb(box, "--deep", "deep_opt")

		# --newuse
		self.newuseCb = self.draw_cb(box, "--newuse", "newuse_opt")
		
		pHolderLabel = gtk.Label("""<u>For the following options, you might use these placeholders:</u>
<b>$(cat)</b> = category
<b>$(pkg)</b> = package-name
<b>$(cat-1)</b>/<b>$(cat-2)</b> = first/second part of the category""")
		pHolderLabel.set_use_markup(True)
		pHolderLabel.set_alignment(0,0)
		box.pack_start(pHolderLabel)

		# The use/mask/keywording checkboxes and edits
		self.usePerVersionCb, self.useFileEdit = self.draw_cb_and_edit(box, "package.use", "usePerVersion_opt", "useFile_opt")
		self.maskPerVersionCb, self.maskFileEdit = self.draw_cb_and_edit(box, "package.mask/package.unmask", "maskPerVersion_opt", "maskFile_opt")
		self.testPerVersionCb, self.testFileEdit = self.draw_cb_and_edit(box, "package.keywords", "testingPerVersion_opt", "testingFile_opt")
		# buttons
		buttonHB = gtk.HButtonBox()
		buttonHB.set_layout(gtk.BUTTONBOX_SPREAD)
		
		okBtn = gtk.Button("_OK")
		cancelBtn = gtk.Button("_Cancel")
		okBtn.connect("clicked", self.cb_ok_clicked)
		cancelBtn.connect("clicked", lambda x: self.window.destroy())
		buttonHB.pack_start(okBtn)
		buttonHB.pack_start(cancelBtn)

		box.pack_start(buttonHB, True, True, 5)

		# finished --> show all
		self.window.show_all()

	def draw_cb_and_edit (self, box, string, cb_opt, edit_opt):
		"""Draws a checkbox and an edit-field. 
		
		@param box: box to place the both things into
		@type box: gtk.Box
		@param string: string to show
		@type string: string
		@param cb_opt: the option string for the Config.const-dict
		@type cb_opt: string
		@param edit_opt: the option string for the Config.const-dic
		@type edit_opt: string

		@return: the checkbox and the edit-field
		@rtype: (gtk.CheckButton, gtk.Edit)"""

		# check-button
		cb = self.draw_cb(box, label=("Add to %s on a per-version-base" % string), opt = cb_opt)

		# edit with label
		hBox = gtk.HBox()
		label = gtk.Label("File name to use if %s is a directory:" % string)
		edit = gtk.Entry()
		edit.set_text(self.cfg.get(self.cfg.const[edit_opt]))
		hBox.pack_start(label, False)
		hBox.pack_start(edit, True, True, 5)
		box.pack_start(hBox, True, True)

		return (cb, edit)

	def draw_cb (self, box, label, opt):
		"""Draws a checkbox.

		@param box: box to place the cb into
		@type box: gtk.Box
		@param label: Label to show
		@type label: string
		@param opt: the option string for the Config.const-dict
		@type opt: string
		@returns: the checkbox
		@rtype: gtk.CheckButton"""

		cb = gtk.CheckButton(label=label)
		cb.set_active(self.cfg.get_boolean(self.cfg.const[opt]))
		box.pack_start(cb, True, True)
		
		return cb

	def _save(self):
		"""Sets all options in the Config-instance."""
		self.cfg.set(self.cfg.const["usePerVersion_opt"], str(self.usePerVersionCb.get_active()))
		self.cfg.set(self.cfg.const["useFile_opt"], self.useFileEdit.get_text())
		self.cfg.set(self.cfg.const["maskPerVersion_opt"], str(self.maskPerVersionCb.get_active()))
		self.cfg.set(self.cfg.const["maskFile_opt"], self.maskFileEdit.get_text())
		self.cfg.set(self.cfg.const["testingPerVersion_opt"], str(self.testPerVersionCb.get_active()))
		self.cfg.set(self.cfg.const["testingFile_opt"], self.testFileEdit.get_text())
		self.cfg.set(self.cfg.const["debug_opt"], str(self.debugCb.get_active()))
		self.cfg.set(self.cfg.const["deep_opt"], str(self.deepCb.get_active()))
		self.cfg.set(self.cfg.const["newuse_opt"], str(self.newuseCb.get_active()))

	def cb_ok_clicked(self, button):
		"""Saves, writes to config-file and closes the window."""
		self._save()
		self.cfg.write()
		self.window.destroy()

class PackageWindow (AbstractDialog):
	"""A window with data about a specfic package."""

	def __init__ (self, parent, cp, queue = None, version = None, delOnClose = True, doEmerge = True):
		"""Build up window contents.
		
		@param parent: the parent window
		@type parent: gtk.Window
		@param cp: the selected package
		@type cp: string (cp)
		@param queue: emerge-queue (if None the emerge-buttons are disabled)
		@type queue: EmergeQueue
		@param version: if not None, specifies the version to select
		@type version: string
		@param delOnClose: if True (default) changed flags are changed on closing
		@type delOnClose: boolean
		@param doEmerge: if False, the emerge buttons are disabled
		@type doEmerge: False"""

		AbstractDialog.__init__(self, parent, cp)

		self.cp = cp # category/package
		self.version = version # version - if not None this is used
		self.queue = queue
		self.delOnClose = delOnClose
		self.doEmerge = doEmerge
		self.flagChanged = False

		# packages and installed packages
		self.packages = backend.sort_package_list(backend.get_all_versions(cp))
		self.instPackages = backend.sort_package_list(backend.get_all_installed_versions(cp))

		# main structure - the table
		self.table = gtk.Table(rows=4,columns=2)
		self.window.add(self.table)

		# version-combo-box
		self.vCombo = self.build_vers_combo()
		self.table.attach(self.vCombo, 0, 1, 1, 2, yoptions = gtk.FILL)
		if not self.doEmerge: self.vCombo.set_sensitive(False)

		# the label (must be here, because it depends on the combo box)
		desc = self.actual_package().get_env_var("DESCRIPTION")
		if not desc: 
			desc = "<no description>"
			use_markup = False
		else:
			desc = "<b>"+desc+"</b>"
			use_markup = True
		self.descLabel = gtk.Label(desc)
		self.descLabel.set_line_wrap(True)
		self.descLabel.set_justify(gtk.JUSTIFY_CENTER)
		self.descLabel.set_use_markup(use_markup)
		self.table.attach(self.descLabel, 0, 2, 0, 1, xoptions = gtk.FILL, ypadding = 10)

		# the check boxes
		checkHB = gtk.HBox (True, 1)
		self.table.attach(checkHB, 1, 2, 1, 2, yoptions = gtk.FILL)

		self.installedCheck = gtk.CheckButton()
		self.installedCheck.connect("button-press-event", self.cb_button_pressed)
		self.installedCheck.set_label("Installed")
		self.installedCheck.set_no_show_all(True)
		checkHB.pack_start(self.installedCheck, True, False)

		self.maskedCheck = gtk.CheckButton()
		self.maskedCheck.connect("toggled", self.cb_masked_toggled)
		self.maskedCheck.set_label("Masked")		
		self.maskedCheck.set_no_show_all(True)
		checkHB.pack_start(self.maskedCheck, True, False)

		self.testingCheck = gtk.CheckButton()
		self.testingCheck.connect("toggled", self.cb_testing_toggled)
		self.testingCheck.set_label("Testing")
		self.testingCheck.set_no_show_all(True)
		checkHB.pack_start(self.testingCheck, True, False)

		self.missing_label = gtk.Label("<span foreground='red'><b>MISSING KEYWORD</b></span>")
		self.missing_label.set_use_markup(True)
		self.missing_label.set_no_show_all(True)
		self.table.attach(self.missing_label, 1, 2, 1, 2, yoptions = gtk.FILL)

		self.not_in_sys_label = gtk.Label("<b>Installed, but not in portage anymore</b>")
		self.not_in_sys_label.set_use_markup(True)
		self.not_in_sys_label.set_no_show_all(True)
		self.table.attach(self.not_in_sys_label, 1, 2, 1, 2, yoptions = gtk.FILL)

		# use list
		self.useList = self.build_use_list()
		self.useListScroll = gtk.ScrolledWindow()
		self.useListScroll.add(self.useList)
		self.useListScroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER) # XXX: make this work correctly
		self.table.attach(self.useListScroll, 0, 2, 2, 3, ypadding = 10)
		
		# buttons
		buttonHB = gtk.HButtonBox()
		buttonHB.set_layout(gtk.BUTTONBOX_SPREAD)
		self.table.attach(buttonHB, 0, 2, 3, 4)
		
		self.emergeBtn = gtk.Button("_Emerge")
		self.unmergeBtn = gtk.Button("_Unmerge")
		if not self.queue or not self.doEmerge: 
			self.emergeBtn.set_sensitive(False)
			self.unmergeBtn.set_sensitive(False)
		self.cancelBtn = gtk.Button("_Cancel")
		if not self.delOnClose:
			self.cancelBtn.set_label("_Close")
		self.cancelBtn.connect("clicked", self.cb_cancel_clicked)
		self.emergeBtn.connect("clicked", self.cb_emerge_clicked)
		self.unmergeBtn.connect("clicked", self.cb_unmerge_clicked)
		buttonHB.pack_start(self.emergeBtn)
		buttonHB.pack_start(self.unmergeBtn)
		buttonHB.pack_start(self.cancelBtn)

		# current status
		self.cb_combo_changed(self.vCombo)

		# show
		self.window.show_all()

	def fill_use_list(self, store):
		"""Fills a given ListStore with the use-flag data.
		
		@param store: the store to fill
		@type store: gtk.ListStore"""

		pkg = self.actual_package()
		pkg_flags = pkg.get_all_use_flags()
		pkg_flags.sort()
		for use in pkg_flags:
			if pkg.is_installed() and use in pkg.get_actual_use_flags(): # flags set during install
				enabled = True
			elif (not pkg.is_installed()) and use in pkg.get_settings("USE").split() and not flags.invert_use_flag(use) in pkg.get_new_use_flags(): # flags that would be set
				enabled = True
			elif use in pkg.get_new_use_flags():
				enabled = True
			else:
				enabled = False
			store.append([enabled, use, backend.get_use_desc(use, self.cp)])
		
		return store

	def build_use_list (self):
		"""Builds the useList."""
		store = gtk.ListStore(bool, str, str)
		self.fill_use_list(store)

		# build view
		view = gtk.TreeView(store)
		cell = gtk.CellRendererText()
		tCell = gtk.CellRendererToggle()
		tCell.set_property("activatable", True)
		tCell.connect("toggled", self.cb_use_flag_toggled, store)
		view.append_column(gtk.TreeViewColumn("Enabled", tCell, active = 0))
		view.append_column(gtk.TreeViewColumn("Flags", cell, text = 1))
		view.append_column(gtk.TreeViewColumn("Description", cell, text = 2))

		if store.iter_n_children(None) == 0: # if there are no nodes in the list ...
			view.set_child_visible(False) # ... do not show the list
		else:
			view.set_child_visible(True)
		return view

	def build_vers_combo (self):
		"""Creates the combo box with the different versions."""
		combo = gtk.combo_box_new_text()

		# append versions
		for s in [x.get_version() for x in self.packages]:
			combo.append_text(s)
		
		# activate the first one
		try:
			best_version = ""
			if self.version:
				best_version = self.version
			else:
				best_version = backend.find_best_match(self.packages[0].get_cp(), (self.instPackages != [])).get_version()
			for i in range(len(self.packages)):
				if self.packages[i].get_version() == best_version:
					combo.set_active(i)
					break
		except AttributeError: # no package found
			debug('catched AttributeError => no "best package" found. Selected first one.')
			combo.set_active(0)

		combo.connect("changed", self.cb_combo_changed)
		
		return combo

	def actual_package (self):
		"""Returns the actual selected package.
		
		@returns: the actual selected package
		@rtype: backend.Package"""
		
		return self.packages[self.vCombo.get_active()]

	def cb_combo_changed (self, combo):
		"""Callback for the changed ComboBox.
		It then rebuilds the useList and the checkboxes."""
		
		# remove old useList
		self.useListScroll.remove(self.useList)
		
		# build new
		self.useList = self.build_use_list()
		self.useListScroll.add(self.useList)
		pkg = self.actual_package()
		
		#
		# rebuild the buttons and checkboxes in all the different manners which are possible
		#
		if (not pkg.is_in_system()) or pkg.is_missing_keyword():
			if not pkg.is_in_system():
				self.missing_label.hide()
				self.not_in_sys_label.show()
			else: # missing keyword
				self.missing_label.show()
				self.not_in_sys_label.hide()
			
			self.installedCheck.hide()
			self.maskedCheck.hide()
			self.testingCheck.hide()
			self.emergeBtn.set_sensitive(False)
		else:
			self.missing_label.hide()
			self.not_in_sys_label.hide()
			self.installedCheck.show()
			self.maskedCheck.show()
			self.testingCheck.show()
			if self.doEmerge:
				self.emergeBtn.set_sensitive(True)
			self.installedCheck.set_active(pkg.is_installed())
			self.maskedCheck.set_active(pkg.is_masked())
			if pkg.is_testing(allowed = False) and not pkg.is_testing(allowed=True):
				self.testingCheck.set_label("<i>(Testing)</i>")
				self.testingCheck.get_child().set_use_markup(True)
			else:
				self.testingCheck.set_label("Testing")
			self.testingCheck.set_active(pkg.is_testing(allowed = False))

		if self.doEmerge:
			# set emerge-button-label
			if not self.actual_package().is_installed():
				self.emergeBtn.set_label("_Emerge")
				self.unmergeBtn.set_sensitive(False)
			else:
				self.emergeBtn.set_label("R_emerge")
				self.unmergeBtn.set_sensitive(True)
		
		# refresh - make window as small as possible
		self.table.show_all()
		self.window.resize(1,1)
		return True

	def cb_button_pressed (self, b, event):
		"""Callback for pressed checkboxes. Just quits the event-loop - no redrawing."""
		if not isinstance(b, gtk.CellRendererToggle):
			b.emit_stop_by_name("button-press-event")
		return True

	def cb_cancel_clicked (self, button, data = None):
		"""Callback for pressed cancel-button. Closes the window."""
		if self.delOnClose: 
			self.actual_package().remove_new_use_flags()
			self.actual_package().remove_new_masked()
			self.actual_package().remove_new_testing()
		elif self.flagChanged:
			if self.queue:
				try:
					try:
						self.queue.append(self.actual_package().get_cpv(), update = True)
					except backend.PackageNotFoundException, e:
						if unmask_dialog(e[0]) == gtk.RESPONSE_YES:
							self.queue.append(self.actual_package().get_cpv(), update = True, unmask = True)
				except backend.BlockedException, e:
					blocked_dialog(e[0], e[1])
					
		self.window.destroy()
		return True

	def cb_emerge_clicked (self, button, data = None):
		"""Callback for pressed emerge-button. Adds the package to the EmergeQueue."""
		if not am_i_root():
			not_root_dialog()
		else:
			try:
				try:
					self.queue.append(self.actual_package().get_cpv(), unmerge = False)
					self.window.destroy()
				except backend.PackageNotFoundException, e:
					if unmask_dialog(e[0]) == gtk.RESPONSE_YES:
						self.queue.append(self.actual_package().get_cpv(), unmerge = False, unmask = True)
						self.window.destroy()
			except BlockedException, e:
				blocked_dialog(e[0], e[1])
		return True

	def cb_unmerge_clicked (self, button, data = None):
		"""Callback for pressed unmerge-button clicked. Adds the package to the UnmergeQueue."""
		if not am_i_root():
			not_root_dialog()
		else:
			try:
				self.queue.append(self.actual_package().get_cpv(), unmerge = True)
			except backend.PackageNotFoundException, e:
				masked_dialog(e[0])

			self.window.destroy()
		return True

	def cb_testing_toggled (self, button):
		"""Callback for toggled testing-checkbox."""
		status = button.get_active()

		if self.actual_package().is_testing(allowed = False) == status:
			return False

		if not self.actual_package().is_testing(allowed = True):
			self.actual_package().set_testing(False)
			button.set_label("Testing")
			button.set_active(True)
		else:
			self.actual_package().set_testing(True)
			if self.actual_package().is_testing(allowed=False):
				button.set_label("<i>(Testing)</i>")
				button.get_child().set_use_markup(True)
				button.set_active(True)
		self.flagChanged = True
		return True

	def cb_masked_toggled (self, button):
		"""Callback for toggled masking-checkbox."""
		status = button.get_active()
		self.actual_package().set_masked(status)
		self.flagChanged = True
		return True

	def cb_use_flag_toggled (self, cell, path, store):
		"""Callback for a toggled use-flag button."""
		store[path][0] = not store[path][0]
		prefix = ""
		if not store[path][0]:
			prefix = "-"
		self.actual_package().set_use_flag(prefix+store[path][1])
		self.flagChanged = True
		return True

class MainWindow:
	"""Application main window."""
	
	def __init__ (self):
		"""Build up window"""
		# window
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_title(("Genetic/One (%s)" % VERSION))
		self.window.connect("destroy", self.cb_destroy)
		self.window.set_border_width(2)
		self.window.set_resizable(True)
		
		mHeight = 800
		if gtk.gdk.screen_height() <= 800: mHeight = 600
		self.window.set_geometry_hints (self.window, min_width = 600, min_height = mHeight, max_height = gtk.gdk.screen_height(), max_width = gtk.gdk.screen_width())

		# booleans
		self.doUpdate = False
		
		# package db
		self.db = Database()
		self.db.populate()

		# config
		self.cfg = Config(CONFIG_LOCATION)
		self.cfg.modify_external_configs()

		# actions needed
		self.emergeAction = gtk.Action("Emerge", "_Emerge", None, None)
		self.emergeAction.connect("activate", self.cb_emerge_clicked)
		self.unmergeAction = gtk.Action("Unmerge", "_Unmerge", None, None)
		self.unmergeAction.connect("activate", self.cb_emerge_clicked)
		self.updateAction = gtk.Action("UpdateWorld", "Update _World", None, None)
		self.updateAction.connect("activate", self.cb_update_clicked)

		# main vb
		vb = gtk.VBox(False, 1)
		self.window.add(vb)

		# menus
		self.uimanager = self.create_uimanager()
		self.queuePopup = self.uimanager.get_widget("/popupQueue")
		menubar = self.uimanager.get_widget("/bar")
		vb.pack_start(menubar, False)
		
		# search
		self.searchEntry = gtk.Entry()
		self.searchBtn = gtk.Button("_Search")
		self.searchBtn.connect("clicked", self.cb_search_clicked)
		self.searchEntry.connect("activate", self.cb_search_clicked)
		hbSearch = gtk.HBox(False, 5)
		hbSearch.pack_start(self.searchEntry, True, True)
		hbSearch.pack_start(self.searchBtn, False, False)
		vb.pack_start(hbSearch, False, False, 5)

		# VPaned holding the lists and the Terminal
		vpaned = gtk.VPaned()
		vpaned.set_position(mHeight/2)
		vb.pack_start(vpaned, True, True)

		# a HB holding the lists
		hb = gtk.HBox(True, 5)
		hbFrame = gtk.Frame()
		hbFrame.add(hb)
		hbFrame.set_shadow_type(gtk.SHADOW_IN)
		vpaned.pack1(hbFrame, shrink = True, resize = True)
		
		self.scroll_1 = gtk.ScrolledWindow()
		self.scroll_2 = gtk.ScrolledWindow()
		self.scroll_1.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		self.scroll_2.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		hb.pack_start(self.scroll_1, True, True)
		hb.pack_start(self.scroll_2, True, True)
		
		# create cat List
		self.catList = self.create_cat_list()
		self.scroll_1.add(self.catList)
		
		# create pkg list
		self.pkgList = self.create_pkg_list()
		self.scroll_2.add(self.pkgList)
		
		# queue list
		queueHB = gtk.HBox(False, 0)
		
		queueScroll = gtk.ScrolledWindow()
		queueScroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		emergeStore = gtk.TreeStore(str,str)
		self.emergeView = gtk.TreeView(emergeStore)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Queue", cell, text = 0)
		self.emergeView.append_column(col)
		col = gtk.TreeViewColumn("Options", cell, markup = 1)
		self.emergeView.append_column(col)
		self.emergeView.connect("row-activated", self.cb_row_activated, emergeStore)
		self.emergeView.connect("button-press-event", self.cb_queue_right_click)
		self.emergeView.set_headers_visible(False)
		queueScroll.add(self.emergeView)
		queueHB.pack_start(queueScroll, True, True)

		# buttons right to the queue list
		buttonBox = gtk.VButtonBox()
		buttonBox.set_layout(gtk.BUTTONBOX_SPREAD)
		queueHB.pack_start(buttonBox, False)
		
		emergeBtn = gtk.Button()
		self.emergeAction.connect_proxy(emergeBtn)
		
		updateBtn = gtk.Button()
		self.updateAction.connect_proxy(updateBtn)

		unmergeBtn = gtk.Button()
		self.unmergeAction.connect_proxy(unmergeBtn)
		
		removeBtn = gtk.Button("_Remove")
		removeBtn.connect("clicked", self.cb_remove_clicked)
		
		buttonBox.pack_start(emergeBtn)
		buttonBox.pack_start(unmergeBtn)
		buttonBox.pack_start(updateBtn)
		buttonBox.pack_start(removeBtn)
		
		# the terminal
		term = vte.Terminal()
		term.set_scrollback_lines(1024)
		term.set_scroll_on_output(True)
		term.set_font_from_string("Monospace 11")
		# XXX why is this not working with the colors
		term.set_color_background(gtk.gdk.color_parse("white"))
		term.set_color_foreground(gtk.gdk.color_parse("black"))
		termBox = gtk.HBox(False, 0)
		termScroll = gtk.VScrollbar(term.get_adjustment())
		termBox.pack_start(term, True, True)
		termBox.pack_start(termScroll, False)
		
		# notebook
		self.notebook = gtk.Notebook()
		self.notebook.append_page(queueHB, gtk.Label("Queue"))
		self.notebook.append_page(termBox, gtk.Label("Console"))

		vpaned.pack2(self.notebook, shrink = True, resize = True)

		# the status line
		self.statusLabel = gtk.Label("Genetic/One - A Portage GUI")
		self.statusLabel.set_alignment(0.0,0.7)
		self.statusLabel.set_single_line_mode(True)
		vb.pack_start(self.statusLabel, False, False)

		# show
		self.window.show_all()

		# set emerge queue
		self.queue = EmergeQueue(console = GtkConsole(term), tree = GtkTree(emergeStore), db = self.db)

	def create_uimanager(self):
		"""Creates a UIManager holding the menubar and the popups.
		@returns: created UIManager
		@rtype: gtk.UIManager"""

		ui ="""
	<ui>
		<menubar name="bar">
			<menu action="File">
				<menuitem action="Prefs" />
				<menuitem action="Reload" />
				<separator />
				<menuitem action="Close" />
			</menu>
			<menu action="EmergeMenu">
				<menuitem action="Emerge" />
				<menuitem action="Unmerge" />
				<menuitem action="UpdateWorld" />
				<menuitem action="Sync" />
			</menu>
			<menu action="Help">
				<menuitem action="About" />
			</menu>
		</menubar>
		<popup name="popupQueue">
			<menuitem action="Oneshot" />
		</popup>
	</ui>"""

		um = gtk.UIManager()
		
		# menubar
		group = gtk.ActionGroup("MenuActions")
		group.add_actions([
			("File", None, "_File"),
			("EmergeMenu", None, "_Emerge"),
			("Help", None, "_?"),
			("Sync", None, "_Sync", None, None, self.cb_sync_clicked),
			("Prefs", None, "_Preferences", None, None, lambda x: PreferenceWindow(self.window, self.cfg)),
			("Reload", None, "_Reload Portage", None, None, self.cb_reload_clicked),
			("Close", None, "_Close", None, None, self.cb_destroy),
			("About", None, "_About", None, None, lambda x: AboutWindow(self.window))])
		# the following actions are defined in __init__, because they are used for buttons too
		group.add_action(self.emergeAction)
		group.add_action(self.unmergeAction)
		group.add_action(self.updateAction)

		um.insert_action_group(group,0)

		# popup
		group = gtk.ActionGroup("PopupActions")
		group.add_actions([
			("Oneshot", None, "Oneshot", None, None, self.cb_oneshot_clicked)])

		um.insert_action_group(group, 1)

		um.add_ui_from_string(ui)
		return um

	def fill_pkg_store (self, store, name = None):
		"""Fills a given ListStore with the packages in a category.
		
		@param store: the store to fill
		@type store: gtk.ListStore
		@param name: the name of the category
		@type name: string
		@returns: the filled store
		@rtype: gtk.ListStore"""

		if name:
			for p in self.db.get_cat(name):
				store.append([p])
		return store
	
	def create_pkg_list (self, name = None):
		"""Creates the package list.
		
		@param name: name of the selected catetegory
		@type name: string
		@returns: the filled package list
		@rtype: gtk.TreeView"""
		
		store = gtk.ListStore(str)
		self.fill_pkg_store(store,name)
		
		# build view
		pkgList = gtk.TreeView(store)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Packages", cell, text = 0)
		pkgList.append_column(col)
		pkgList.connect("row-activated", self.cb_row_activated, store)

		return pkgList

	def create_cat_list (self):
		"""Creates the category list.
		
		@returns: created view
		@rtype: gtk.TreeView"""
		
		store = gtk.ListStore(str)

		# build categories
		for p in backend.list_categories():
			store.append([p])
		# sort them alphabetically
		store.set_sort_column_id(0, gtk.SORT_ASCENDING)

		view = gtk.TreeView(store)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Categories", cell, text = 0)
		view.append_column(col)
		view.connect("cursor-changed", self.cb_cat_list_selection)
		view.connect("row-activated", lambda v,p,c : self.cb_cat_list_selection(v))
		view.set_search_column(0)

		return view

	def jump_to (self, cp):
		"""Is called when we want to jump to a specific package."""
		PackageWindow(self.window, cp, self.queue)
	
	def cb_destroy (self, widget, data = None):
		"""Calls main_quit()."""
		gtk.main_quit()

	def cb_cat_list_selection (self, view):
		"""Callback for a category-list selection. Updates the package list with the packages in the category."""
		# get the selected category
		sel = view.get_selection()
		store, it = sel.get_selected()
		if it:
			self.selCatName = store.get_value(it, 0)
			self.pkgList.get_model().clear()
			self.fill_pkg_store(self.pkgList.get_model(), self.selCatName)
		return True

	def cb_row_activated (self, view, path, col, store = None):
		"""Callback for an activated row in the pkgList or in the emergeQueue. Opens a package window."""
		if view == self.pkgList:
			package = store.get_value(store.get_iter(path), 0)
			if package[-1] == '*': package = package[:-1]
			PackageWindow(self.window, self.selCatName+"/"+package, self.queue)
		elif view == self.emergeView:
			if len(path) > 1:
				package = store.get_value(store.get_iter(path), 0)
				cat, name, vers, rev = backend.split_package_name(package)
				if rev != "r0": vers = vers+"-"+rev
				PackageWindow(self.window, cat+"/"+name, queue = self.queue, version = vers, delOnClose = False, doEmerge = False)
		return True

	def cb_remove_clicked (self, button):
		"""Removes a selected item in the (un)emerge-queue if possible."""
		selected = self.emergeView.get_selection()

		if selected:
			model, iter = selected.get_selected()
			
			if iter == None: return False

			if not model.iter_parent(iter): # top-level
				if model.iter_n_children(iter) > 0: # and has children which can be removed :)
					if remove_queue_dialog() == gtk.RESPONSE_YES :
						self.queue.remove_children(iter)
						self.doUpdate = False
			
			elif model.iter_parent(model.iter_parent(iter)): # this is in the 3rd level => dependency
				remove_deps_dialog()
			else:
				self.queue.remove_children(iter) # remove children first
				self.queue.remove(iter)
				self.doUpdate = False
		
		return True

	def cb_emerge_clicked (self, action):
		"""Do emerge or unemerge."""
		
		self.notebook.set_current_page(1)
		
		if action == self.emergeAction:
			if len(flags.newUseFlags) > 0:
				changed_flags_dialog("use flags")
				flags.write_use_flags()
			
			if len(flags.new_masked)>0 or len(flags.new_unmasked)>0 or len(flags.newTesting)>0:
				changed_flags_dialog("masking keywords")
				flags.write_masked()
				flags.write_testing()
				backend.reload_settings()
			
			if not self.doUpdate:
				self.queue.emerge(force=True)
			else:
				self.queue.update_world(force=True, newuse = self.cfg.get_boolean(self.cfg.const["newuse_opt"]), deep = self.cfg.get_boolean(self.cfg.const["deep_opt"]))
				self.doUpdate = False
		
		elif action == self.unmergeAction:
			self.queue.unmerge(force=True)

		return True

	def watch_cursor (func):
		"""This is a decorator for functions being so time consuming, that it is appropriate to show the watch-cursor.
		@attention: this function relies on the gtk.Window-Object being stored as self.window"""
		def wrapper (self, *args, **kwargs):
			ret = None
			def cb_idle():
				try:
					ret = func(self, *args, **kwargs)
				finally:
					self.window.window.set_cursor(None)
				return False
			
			watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
			self.window.window.set_cursor(watch)
			gobject.idle_add(cb_idle)
			return ret
		return wrapper

	@watch_cursor
	def cb_update_clicked (self, action):
		if not backend.am_i_root():
			not_root_dialog()
		
		else:
			updating = backend.update_world(newuse = self.cfg.get_boolean(self.cfg.const["newuse_opt"]), deep = self.cfg.get_boolean(self.cfg.const["deep_opt"]))

			debug("updating list:", [(x.get_cpv(), y.get_cpv()) for x,y in updating])
			try:
				for pkg, old_pkg in updating:
					self.queue.append(pkg.get_cpv())
			except BlockedException, e:
				blocked_dialog(e[0], e[1])
			if len(updating): self.doUpdate = True
		return True

	def cb_sync_clicked (self, action):
		self.notebook.set_current_page(1)
		self.queue.sync()
	
	@watch_cursor
	def cb_reload_clicked (self, action):
		"""Reloads the portage settings and the database."""
		backend.reload_settings()
		del self.db
		self.db = Database()
		self.db.populate()
	
	@watch_cursor
	def cb_search_clicked (self, button, data = None):
		"""Do a search."""
		if self.searchEntry.get_text() != "":
			packages = backend.find_all_packages(self.searchEntry.get_text(), withVersion = False)

			if packages == []:
				nothing_found_dialog()
			else:
				if len(packages) == 1:
					self.jump_to(packages[0])
				else:
					SearchWindow(self.window, packages, self.jump_to)

	def cb_queue_right_click (self, queue, event):
		if event.button == 3:
			x = int(event.x)
			y = int(event.y)
			time = event.time
			pthinfo = queue.get_path_at_pos(x, y)
			if pthinfo is not None:
				path, col, cellx, celly = pthinfo
				queue.grab_focus()
				queue.set_cursor(path, col, 0)
				self.queuePopup.popup(None, None, None, event.button, time)
				return True
			else:
				return False

	def cb_oneshot_clicked (self, action):
		sel = self.emergeView.get_selection()
		store, it = sel.get_selected()
		if it:
			package = store.get_value(it, 0)
			if not self.cfg.get_local(package, self.cfg.const["oneshot_opt"]):
				set = True
			else:
				set = False
			
			self.cfg.set_local(package, self.cfg.const["oneshot_opt"], set)
			self.queue.append(package, update = True, oneshot = set, forceUpdate = True)
			

	def main (self):
		"""Main."""
		gobject.threads_init() 
		# now subthreads can run normally, but are not allowed to touch the GUI. If threads should change sth there - use gobject.idle_add().
		# for more informations on threading and gtk: http://www.async.com.br/faq/pygtk/index.py?req=show&file=faq20.006.htp
		gtk.main()
