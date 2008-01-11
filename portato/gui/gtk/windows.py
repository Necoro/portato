# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/windows.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

# gtk stuff
import gtk
import gobject

# other
import os.path
from subprocess import Popen
from gettext import lgettext as _

# our backend stuff
from ... import get_listener, plugin
from ...helper import debug, warning, error, unique_array
from ...session import Session
from ...constants import CONFIG_LOCATION, VERSION, APP_ICON
from ...backend import flags, system
from ...backend.exceptions import PackageNotFoundException, BlockedException

# more GUI stuff
from ..gui_helper import Database, Config, EmergeQueue
from .basic import Window, AbstractDialog, Popup
from .wrapper import GtkTree, GtkConsole
from .exception_handling import GtkThread
from .views import LogView, HighlightView
from .dialogs import (blocked_dialog, changed_flags_dialog, io_ex_dialog,
		nothing_found_dialog, queue_not_empty_dialog, remove_deps_dialog,
		remove_queue_dialog, unmask_dialog)

class AboutWindow (AbstractDialog):
	"""A window showing the "about"-informations."""

	def __init__ (self, parent):

		AbstractDialog.__init__(self, parent)

		img = gtk.Image()
		img.set_from_file(APP_ICON)

		self.window.set_version(VERSION)
		self.window.set_logo(img.get_pixbuf())

		self.window.show_all()

class PluginWindow (AbstractDialog):
	
	def __init__ (self, parent, plugins):
		"""Constructor.

		@param parent: the parent window
		@type parent: gtk.Window"""
		
		AbstractDialog.__init__(self, parent)
		self.plugins = plugins
		self.changedPlugins = {}

		view = self.tree.get_widget("pluginList")
		self.store = gtk.ListStore(str,str,bool)
		
		view.set_model(self.store)
		
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn(_("Plugin"), cell, markup = 0)
		view.append_column(col)
		
		col = gtk.TreeViewColumn(_("Authors"), cell, text = 1)
		view.append_column(col)

		bcell = gtk.CellRendererToggle()
		bcell.connect("toggled", self.cb_plugin_toggled)
		col = gtk.TreeViewColumn(_("Enabled"), bcell, active = 2)
		view.append_column(col)
		
		for p in (("<b>"+p.name+"</b>", p.author, p.is_enabled()) for p in plugins):
			self.store.append(p)

		self.window.show_all()

	def cb_plugin_toggled (self, cell, path):
		path = int(path)
		self.store[path][2] = not self.store[path][2]

		self.changedPlugins.update({self.plugins[path] : self.store[path][2]})

	def cb_ok_clicked (self, btn):
		for plugin, val in self.changedPlugins.iteritems():
			plugin.set_option("disabled", not val)

		self.close()
		return True

class UpdateWindow (AbstractDialog):

	def __init__ (self, parent, packages, queue, jump_to):
		AbstractDialog.__init__(self, parent)

		self.queue = queue
		self.jump = jump_to

		self.packages = system.sort_package_list(packages)

		self.build_list()

		self.window.show_all()

	def build_list (self):

		store = gtk.ListStore(bool, str)
		self.view = self.tree.get_widget("packageList")
		self.view.set_model(store)

		cell = gtk.CellRendererText()
		tCell = gtk.CellRendererToggle()
		tCell.set_property("activatable", True)
		tCell.connect("toggled", self.cb_check_toggled) # emulate the normal toggle behavior ...
		
		self.view.append_column(gtk.TreeViewColumn(_("Enabled"), tCell, active = 0))
		self.view.append_column(gtk.TreeViewColumn(_("Package"), cell, text = 1))

		for p in self.packages:
			store.append([False, p.get_cpv()])

	def cb_set_size (self, *args):
		"""
		This callback is called shortly before drawing.
		It calculates the optimal size of the window.
		The optimum is defined as: as large as possible w/o scrollbars
		"""

		bb = self.tree.get_widget("updateBB")
		vals = (self.view.get_vadjustment().upper+bb.size_request()[1]+10, # max size of list + size of BB + constant
				self.parent.get_size()[1]) # size of the parent -> maximum size
		debug("Size values for the list and for the parent: %d / %d", *vals)
		val = int(min(vals))
		debug("Minimum value: %d", val)
		self.window.set_geometry_hints(self.window, min_height = val)

	def cb_select_all_clicked (self, btn):
		model = self.view.get_model()
		iter = model.get_iter_first()
		
		while iter:
			model.set_value(iter, 0, True)
			iter = model.iter_next(iter)

		return True

	def cb_install_clicked (self, btn):
		model = self.view.get_model()
		iter = model.get_iter_first()
		if iter is None: return

		items = []
		while iter:
			if model.get_value(iter, 0):
				items.append(model.get_value(iter, 1))
			iter = model.iter_next(iter)
		
		for item in items:
			try:
				try:
					self.queue.append(item, unmerge = False, oneshot = True)
				except PackageNotFoundException, e:
					if unmask_dialog(e[0]) == gtk.RESPONSE_YES :
						self.queue.append(item, unmerge = False, unmask = True, oneshot = True)

			except BlockedException, e:
				blocked_dialog(e[0], e[1])

		self.close()
		return True

	def cb_package_selected (self, view):
		sel = view.get_selection()
		store, it = sel.get_selected()
		if it:
			package = system.new_package(store.get_value(it, 1))

			self.jump(package.get_cp(), package.get_version())

		return True

	def cb_check_toggled (self, cell, path):
		# for whatever reason we have to define normal toggle behavior explicitly
		store = self.view.get_model()
		store[path][0] = not store[path][0]
		return True


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
		
		AbstractDialog.__init__(self, parent)
		
		self.jump_to = jump_to # function to call for jumping
		self.list = list
		self.list.sort()
		
		# combo box
		self.searchList = self.tree.get_widget("searchList")
		self.build_sort_list()
		self.searchList.get_selection().select_path(0)

		# finished --> show
		self.window.show_all()

	def build_sort_list (self):
		"""Builds the sort list."""
		
		store = gtk.ListStore(str)
		self.searchList.set_model(store)

		# build categories
		for p in self.list:
			store.append(["%s/<b>%s</b>" % tuple(p.split("/"))])

		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn(_("Results"), cell, markup = 0)
		self.searchList.append_column(col)

	def ok (self, *args):
		self.jump()
		self.close()
	
	def jump (self, *args):
		model, iter = self.searchList.get_selection().get_selected()
		self.jump_to(self.list[model.get_path(iter)[0]])

	def cb_key_pressed_combo (self, widget, event):
		"""Emulates a ok-button-click."""
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == "Return": # take it as an "OK" if Enter is pressed
			self.jump()
			return True
		else:
			return False

class PreferenceWindow (AbstractDialog):
	"""Window displaying some preferences."""
	
	# all checkboxes in the window
	# widget name -> option name
	checkboxes = {
			"debugCheck"			: "debug",
			"deepCheck"				: "deep",
			"newUseCheck"			: "newuse",
			"maskPerVersionCheck"	: "maskPerVersion",
			"minimizeCheck"			: ("hideOnMinimize", "GUI"),
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

	def __init__ (self, parent, cfg, set_console_font):
		"""Constructor.

		@param parent: parent window
		@type parent: gtk.Window
		@param cfg: configuration object
		@type cfg: gui_helper.Config
		@param set_console_font: function to call to set the console font
		@type set_console_font: function(string)"""
		
		AbstractDialog.__init__(self, parent)

		# our config
		self.cfg = cfg

		# the console font setter
		self.set_console_font = set_console_font
		
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
		self.consoleFontBtn.set_font_name(self.cfg.get("consolefont", section = "GTK"))

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
		self.cfg.set("consolefont", font, section = "GTK")
		self.set_console_font(font)
		
		gtk.link_button_set_uri_hook(lambda btn, x: get_listener().send_cmd([self.cfg.get("browserCmd", section = "GUI"), btn.get_uri()]))

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


class PackageTable:
	"""A window with data about a specfic package."""

	def __init__ (self, main):
		"""Build up window contents.
		
		@param main: the main window
		@type main: MainWindow"""

		self.main = main
		self.tree = main.tree
		self.window = main.window
		self.tree.signal_autoconnect(self)
		
		# the table
		self.table = self.tree.get_widget("PackageTable")
		
		# the version list
		self.versList = self.tree.get_widget("versionList")
		self.build_vers_list()

		# chechboxes
		self.installedCheck = self.tree.get_widget("installedCheck")
		self.maskedCheck = self.tree.get_widget("maskedCheck")
		self.testingCheck = self.tree.get_widget("testingCheck")

		# labels
		self.descLabel = self.tree.get_widget("descLabel")
		self.notInSysLabel = self.tree.get_widget("notInSysLabel")
		self.missingLabel = self.tree.get_widget("missingLabel")
		
		# link
		self.pkgLinkBox = self.tree.get_widget("pkgLinkBox")

		# buttons
		self.emergeBtn = self.tree.get_widget("pkgEmergeBtn")
		self.unmergeBtn = self.tree.get_widget("pkgUnmergeBtn")
		self.cancelBtn = self.tree.get_widget("pkgCancelBtn")
		self.ebuildBtn = self.tree.get_widget("pkgEbuildBtn")
		
		# useList
		self.useList = self.tree.get_widget("useList")
		self.build_use_list()

	def update (self, cp, queue = None, version = None, doEmerge = True, instantChange = False):
		"""Updates the table to show the contents for the package.
		
		@param cp: the selected package
		@type cp: string (cp)
		@param queue: emerge-queue (if None the emerge-buttons are disabled)
		@type queue: EmergeQueue
		@param version: if not None, specifies the version to select
		@type version: string
		@param doEmerge: if False, the emerge buttons are disabled
		@type doEmerge: boolean
		@param instantChange: if True the changed keywords are updated instantly
		@type instantChange: boolean"""
		
		self.cp = cp # category/package
		self.version = version # version - if not None this is used
		self.queue = queue
		self.doEmerge = doEmerge
		self.instantChange = instantChange

		# packages and installed packages
		if not self.doEmerge:
			self.instPackages = self.packages = system.find_packages("=%s-%s" % (cp, version), masked = True)
		else:
			self.packages = system.sort_package_list(system.find_packages(cp, masked = True))
			self.instPackages = system.sort_package_list(system.find_installed_packages(cp, masked = True))

		# version-combo-box
		self.versList.get_model().clear()
		self.fill_vers_list()

		if not self.queue or not self.doEmerge: 
			self.emergeBtn.set_sensitive(False)
			self.unmergeBtn.set_sensitive(False)
		
		# current status
		self.cb_vers_list_changed()
		self.table.show_all()

	def hide (self):
		self.table.hide_all()

	def set_desc_label (self):
		desc = self.actual_package().get_package_settings("DESCRIPTION").replace("&","&amp;")
		if not desc: 
			desc = _("<no description>")
			use_markup = False
		else:
			desc = "<b>"+desc+"</b>"
			use_markup = True
		name = "<i><u>"+self.actual_package().get_cp()+"</u></i>"
		if self.actual_package().is_overlay():
			name = "%s\n<i>(Overlay: %s)</i>" % (name, self.actual_package().get_overlay_path())

		desc = "%s\n\n%s" % (name, desc)

		self.descLabel.set_use_markup(use_markup)
		self.descLabel.set_label(desc)

	def fill_use_list(self):

		pkg = self.actual_package()
		pkg_flags = flags.sort_use_flag_list(pkg.get_iuse_flags(keep = True))
	
		actual_exp = None
		actual_exp_it = None

		euse = pkg.get_actual_use_flags()
		instuse = pkg.get_installed_use_flags()

		store = self.useList.get_model()

		for use in pkg_flags:
			if use.startswith(("+","-")):
				forced = (use[0] == "+")
				use = use[1:]
			else:
				forced = None

			exp = pkg.use_expanded(use, suggest = actual_exp)
			if exp is not None:
				if exp != actual_exp:
					actual_exp_it = store.append(None, [None, None, exp, "<i>%s</i>" % _("This is an expanded use flag and cannot be selected")])
					actual_exp = exp
			else:
				actual_exp_it = None
				actual_exp = None

			enabled = forced or use in euse
			installed = use in instuse
			store.append(actual_exp_it, [enabled, installed, use, system.get_use_desc(use, self.cp)])
		
	def build_use_list (self):
		"""Builds the useList."""
		store = gtk.TreeStore(bool, bool, str, str)
		self.useList.set_model(store)

		# build view
		cell = gtk.CellRendererText()
		iCell = gtk.CellRendererToggle()
		iCell.set_property("activatable", False)
		tCell = gtk.CellRendererToggle()
		tCell.set_property("activatable", True)
		tCell.connect("toggled", self.cb_use_flag_toggled, store)
		self.useList.append_column(gtk.TreeViewColumn(_("Enabled"), tCell, active = 0))
		self.useList.append_column(gtk.TreeViewColumn(_("Installed"), iCell, active = 1))
		self.useList.append_column(gtk.TreeViewColumn(_("Flag"), cell, text = 2))
		self.useList.append_column(gtk.TreeViewColumn(_("Description"), cell, markup = 3))

		self.useList.set_search_column(2)
		self.useList.set_enable_tree_lines(True)

	def build_vers_list (self):
		"""Builds the package list.

		@param name: name of the selected catetegory
		@type name: string"""

		store = gtk.ListStore(gtk.gdk.Pixbuf, str)

		# build view
		self.versList.set_model(store)
		col = gtk.TreeViewColumn(("Versions"))

		# adding the pixbuf
		cell = gtk.CellRendererPixbuf()
		col.pack_start(cell, False)
		col.add_attribute(cell, "pixbuf", 0)

		# adding the package name
		cell = gtk.CellRendererText()
		col.pack_start(cell, True)
		col.add_attribute(cell, "text", 1)

		self.versList.append_column(col)
		
	def fill_vers_list (self):
		
		store = self.versList.get_model()
		# append versions
		for vers, inst in ((x.get_version(), x.is_installed()) for x in self.packages):
			if inst:
				icon = self.main.instPixbuf
			else:
				icon = None
			store.append([icon, vers])
		
		sel = self.versList.get_selection()

		# activate the first one
		try:
			best_version = ""
			if self.version:
				best_version = self.version
			else:
				best_version = system.find_best_match(self.packages[0].get_cp(), only_installed = (self.instPackages != [])).get_version()
			for i in range(len(self.packages)):
				if self.packages[i].get_version() == best_version:
					sel.select_path((i,))
					break
		except AttributeError: # no package found
			sel.select_path((0,))

	def actual_package (self):
		"""Returns the actual selected package.
		
		@returns: the actual selected package
		@rtype: backend.Package"""
		
		model, iter = self.versList.get_selection().get_selected()
		return self.packages[model.get_path(iter)[0]]

	def _update_keywords (self, emerge, update = False):
		if emerge:
			try:
				try:
					self.queue.append(self.actual_package().get_cpv(), unmerge = False, update = update)
				except PackageNotFoundException, e:
					if unmask_dialog(e[0]) == gtk.RESPONSE_YES:
						self.queue.append(self.actual_package().get_cpv(), unmerge = False, unmask = True, update = update)
			except BlockedException, e:
				blocked_dialog(e[0], e[1])
		else:
			try:
				self.queue.append(self.actual_package().get_cpv(), unmerge = True)
			except PackageNotFoundException, e:
				error(_("Package could not be found: %s"), e[0])
				#masked_dialog(e[0])

	def cb_vers_list_changed (self, *args):

		pkg = self.actual_package()
		self.main.ebuildView.update(pkg)
		self.main.ebuildView.get_parent().show_all()
		self.main.changelogView.update(pkg)
		self.main.changelogView.get_parent().show_all()
		
		self.set_desc_label()

		for c in self.pkgLinkBox.get_children():
			self.pkgLinkBox.remove(c)

		self.pkgLinkBox.add(gtk.LinkButton(pkg.get_package_settings("HOMEPAGE")))

		# set use list
		self.useList.get_model().clear()
		self.useList.columns_autosize()
		self.fill_use_list()
		
		#
		# rebuild the buttons and checkboxes in all the different manners which are possible
		#
		if (not pkg.is_in_system()) or pkg.is_missing_keyword():
			if not pkg.is_in_system():
				self.missingLabel.hide()
				self.notInSysLabel.show()
			else: # missing keyword
				self.missingLabel.show()
				self.notInSysLabel.hide()
			
			self.installedCheck.hide()
			self.maskedCheck.hide()
			self.testingCheck.hide()
			self.emergeBtn.set_sensitive(False)
		else: # normal package
			self.missingLabel.hide()
			self.notInSysLabel.hide()
			self.installedCheck.show()
			self.maskedCheck.show()
			self.testingCheck.show()
			if self.doEmerge:
				self.emergeBtn.set_sensitive(True)
			self.installedCheck.set_active(pkg.is_installed())
			
			gtk.Tooltips().set_tip(self.maskedCheck, pkg.get_masking_reason()) # this returns None if it is not masked =)
			if pkg.is_masked(use_changed = False) and not pkg.is_masked(use_changed = True):
				self.maskedCheck.set_label("<i>(%s)</i>" % _("Masked"))
				self.maskedCheck.get_child().set_use_markup(True)
			else:
				self.maskedCheck.set_label(_("Masked"))
			
			if pkg.is_locally_masked():
				self.maskedCheck.set_label("<b>%s</b>" % _("Masked"))
				self.maskedCheck.get_child().set_use_markup(True)
				self.maskedCheck.set_active(True)
			else:
				self.maskedCheck.set_active(pkg.is_masked(use_changed = False))
			
			if pkg.is_testing(use_keywords = False) and not pkg.is_testing(use_keywords = True):
				self.testingCheck.set_label("<i>(%s)</i>" % _("Testing"))
				self.testingCheck.get_child().set_use_markup(True)
			else:
				self.testingCheck.set_label(_("Testing"))
			
			self.testingCheck.set_active(pkg.is_testing(use_keywords = False))

		if self.doEmerge:
			# set emerge-button-label
			if not self.actual_package().is_installed():
				self.unmergeBtn.set_sensitive(False)
			else:
				self.unmergeBtn.set_sensitive(True)
		
		self.table.show_all()

		return True

	def cb_button_pressed (self, b, event):
		"""Callback for pressed checkboxes. Just quits the event-loop - no redrawing."""
		if not isinstance(b, gtk.CellRendererToggle):
			b.emit_stop_by_name("button-press-event")
		return True

	def cb_package_revert_clicked (self, button):
		"""Callback for pressed revert-button."""
		self.actual_package().remove_new_use_flags()
		self.actual_package().remove_new_masked()
		self.actual_package().remove_new_testing()
		self.versList.get_model().clear()
		self.fill_vers_list()
		self.cb_vers_list_changed()
		if self.instantChange:
			self._update_keywords(True, update = True)
		return True

	def cb_package_emerge_clicked (self, button):
		"""Callback for pressed emerge-button. Adds the package to the EmergeQueue."""
		self._update_keywords(True)
		self.main.notebook.set_current_page(self.main.QUEUE_PAGE)
		return True

	def cb_package_unmerge_clicked (self, button):
		"""Callback for pressed unmerge-button clicked. Adds the package to the UnmergeQueue."""
		self._update_keywords(False)
		self.main.notebook.set_current_page(self.main.QUEUE_PAGE)
		return True

	def cb_testing_toggled (self, button):
		"""Callback for toggled testing-checkbox."""
		status = button.get_active()

		if self.actual_package().is_testing(use_keywords = False) == status:
			return False

		if not self.actual_package().is_testing(use_keywords = True):
			self.actual_package().set_testing(False)
			button.set_label(_("Testing"))
			button.set_active(True)
		else:
			self.actual_package().set_testing(True)
			if self.actual_package().is_testing(use_keywords=False):
				button.set_label("<i>(%s)</i>" % _("Testing"))
				button.get_child().set_use_markup(True)
				button.set_active(True)

		if self.instantChange:
			self._update_keywords(True, update = True)
		
		return True

	def cb_masked_toggled (self, button):
		"""Callback for toggled masking-checkbox."""
		status = button.get_active()
		pkg = self.actual_package()

		if pkg.is_masked(use_changed = False) == status and not pkg.is_locally_masked():
			return False

		if pkg.is_locally_masked() and status:
			return False
	
		if not pkg.is_masked(use_changed = True):
			pkg.set_masked(True)
			if pkg.is_locally_masked():
				button.set_label("<b>%s</b>" % _("Masked"))
				button.get_child().set_use_markup(True)
			else:
				button.set_label(_("Masked"))

			button.set_active(True)
		else:
			locally = pkg.is_locally_masked()
			pkg.set_masked(False)
			if pkg.is_masked(use_changed=False) and not locally:
				button.set_label("<i>(%s)</i>" % _("Masked"))
				button.get_child().set_use_markup(True)
				button.set_active(True)
			else:
				button.set_label(_("Masked"))
		
		if self.instantChange:
			self._update_keywords(True, update = True)
		
		return True

	def cb_use_flag_toggled (self, cell, path, store):
		"""Callback for a toggled use-flag button."""
		flag = store[path][2]
		pkg = self.actual_package()
		
		if flag in pkg.get_global_settings("USE_EXPAND").split(): # ignore expanded flags
			return False

		store[path][0] = not store[path][0]
		prefix = ""
		if not store[path][0]:
			prefix = "-"
		
		pkg.set_use_flag(prefix+flag)	
		if self.instantChange:
			self._update_keywords(True, update = True)
	
		return True

class MainWindow (Window):
	"""Application main window."""

	# NOTEBOOK PAGE CONSTANTS
	(
			PKG_PAGE,
			EBUILD_PAGE,
			CHANGELOG_PAGE,
			QUEUE_PAGE,
			CONSOLE_PAGE,
			LOG_PAGE
	) = range(6)

	def __init__ (self, splash = None):	
		"""Build up window"""

		if splash is None:
			splash = lambda x: True
		
		# the title
		self.main_title = "Portato (%s)" % VERSION

		# main window stuff
		Window.__init__(self)
		self.window.set_title(self.main_title)
		self.window.set_geometry_hints (self.window, max_height = gtk.gdk.screen_height(), max_width = gtk.gdk.screen_width())
		
		# booleans
		self.doUpdate = False
		self.showAll = True # show only installed or all packages?

		# installed pixbuf
		self.instPixbuf = self.window.render_icon(gtk.STOCK_YES, gtk.ICON_SIZE_MENU)
		
		# get the logging window as soon as possible
		self.logView = LogView(self.tree.get_widget("logView"))
		
		# config
		splash(_("Loading Config"))
		try:
			self.cfg = Config(CONFIG_LOCATION)
		except IOError, e:
			io_ex_dialog(e)
			raise

		self.cfg.modify_external_configs()
		gtk.link_button_set_uri_hook(lambda btn, x: get_listener().send_cmd([self.cfg.get("browserCmd", section = "GUI"), btn.get_uri()]))
		gtk.about_dialog_set_url_hook(lambda *args: True) # dummy - if not set link is not set as link; if link is clicked the normal uuri_hook is called too - thus do not call browser here

		# package db
		splash(_("Creating Database"))
		self.db = Database()
		self.db.populate()
		
		# set plugins and plugin-menu
		splash(_("Loading Plugins"))

		plugin.load_plugins("gtk")
		menus = plugin.get_plugin_queue().get_plugin_menus()
		if menus:
			self.tree.get_widget("pluginMenuItem").set_no_show_all(False)
			pluginMenu = self.tree.get_widget("pluginMenu")

			for m in menus:
				item = gtk.MenuItem(m.label)
				item.connect("activate", m.call)
				pluginMenu.append(item)

		splash(_("Building frontend"))
		# set vpaned position
		self.vpaned = self.tree.get_widget("vpaned")
		self.vpaned.set_position(int(self.window.get_size()[1]/2))

		# cat and pkg list
		self.sortPkgListByName = True
		self.catList = self.tree.get_widget("catList")
		self.pkgList = self.tree.get_widget("pkgList")
		self.build_cat_list()
		self.build_pkg_list()

		# queue list
		self.queueList = self.tree.get_widget("queueList")
		self.build_queue_list()

		# the terminal
		self.console = GtkConsole()
		self.termHB = self.tree.get_widget("termHB")
		self.build_terminal()
		

		# popups
		self.queuePopup = Popup("queuePopup", self)
		self.consolePopup = Popup("consolePopup", self)
		self.trayPopup = Popup("systrayPopup", self)

		# pause menu items
		self.emergePaused = False
		self.pauseItems = {}
		self.pauseItems["tray"] = self.trayPopup.tree.get_widget("pauseItemTray")
		self.pauseItems["popup"] = self.consolePopup.tree.get_widget("pauseItemPopup")
		self.pauseItems["menu"] = self.tree.get_widget("pauseItemMenu")

		for k,v in self.pauseItems.items():
			self.pauseItems[k] = (v, v.connect_after("activate", self.cb_pause_emerge(k)))

		# systray
		if self.cfg.get_boolean("showSystray", "GUI"):
			self.tray = gtk.status_icon_new_from_file(APP_ICON)
			self.tray.connect("activate", self.cb_systray_activated)
			self.tray.connect("popup-menu", lambda icon, btn, time: self.trayPopup.popup(None, None, None, btn, time))
		else:
			self.tray = None

		# set emerge queue
		self.queueTree = GtkTree(self.queueList.get_model())
		self.queue = EmergeQueue(console = self.console, tree = self.queueTree, db = self.db, title_update = self.title_update, threadClass = GtkThread)
		
		# session
		splash(_("Restoring Session"))
		self.load_session()
		
		splash(_("Finishing startup"))
		
		# notebook
		self.notebook = self.tree.get_widget("notebook")
		self.window.show_all()
		
		# the hidden stuff
		ebuildScroll = self.tree.get_widget("ebuildScroll")
		self.ebuildView = HighlightView(lambda p: p.get_ebuild_path(), ["gentoo", "sh"])
		ebuildScroll.add(self.ebuildView)
		ebuildScroll.hide_all()

		changelogScroll = self.tree.get_widget("changelogScroll")
		self.changelogView = HighlightView(lambda p: os.path.join(p.get_package_path(), "ChangeLog"), ["changelog"])
		changelogScroll.add(self.changelogView)
		changelogScroll.hide_all()
		
		# table
		self.packageTable = PackageTable(self)
		self.packageTable.hide()
	
	def show_package (self, *args, **kwargs):
		self.packageTable.update(*args, **kwargs)
		self.notebook.set_current_page(self.PKG_PAGE)

	def build_terminal (self):
		"""Builds the terminal."""
		
		self.console.set_scrollback_lines(1024)
		self.console.set_scroll_on_output(True)
		self.console.set_font_from_string(self.cfg.get("consolefont", "GTK"))
		self.console.connect("button-press-event", self.cb_right_click)
		termScroll = gtk.VScrollbar(self.console.get_adjustment())
		self.termHB.pack_start(self.console, True, True)
		self.termHB.pack_start(termScroll, False)

	def build_queue_list (self):
		"""Builds the queue list."""

		store = gtk.TreeStore(str,str)
		
		self.queueList.set_model(store)
		
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn(_("Queue"), cell, text = 0)
		self.queueList.append_column(col)
		
		col = gtk.TreeViewColumn(_("Options"), cell, markup = 1)
		self.queueList.append_column(col)

	def build_cat_list (self):
		"""Builds the category list."""
		
		store = gtk.ListStore(str)

		self.catList.set_model(store)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn(_("Categories"), cell, text = 0)
		self.catList.append_column(col)

		self.fill_cat_store(store)

	def fill_cat_store (self, store):
		
		if self.showAll:
			cats = system.list_categories() 
		else:
			cats = self.db.get_installed_categories()

		for p in cats:
			store.append([p])
		
		# sort them alphabetically
		store.set_sort_column_id(0, gtk.SORT_ASCENDING)

	def build_pkg_list (self, name = None):
		"""Builds the package list.
		
		@param name: name of the selected catetegory
		@type name: string"""
		
		store = gtk.ListStore(gtk.gdk.Pixbuf, str)
		self.fill_pkg_store(store,name)
		
		# build view
		self.pkgList.set_model(store)
		
		col = gtk.TreeViewColumn(_("Packages"))
		col.set_clickable(True)
		col.connect("clicked", self.cb_pkg_list_header_clicked)

		# adding the pixbuf
		cell = gtk.CellRendererPixbuf()
		col.pack_start(cell, False)
		col.add_attribute(cell, "pixbuf", 0)
		
		# adding the package name
		cell = gtk.CellRendererText()
		col.pack_start(cell, True)
		col.add_attribute(cell, "text", 1)
		
		self.pkgList.append_column(col)

	def fill_pkg_store (self, store, name = None):
		"""Fills a given ListStore with the packages in a category.
		
		@param store: the store to fill
		@type store: gtk.ListStore
		@param name: the name of the category
		@type name: string
		@returns: the filled store
		@rtype: gtk.ListStore"""

		if name:
			for pkg, is_inst in self.db.get_cat(name, self.sortPkgListByName):
				if is_inst:
					icon = self.instPixbuf
				elif not self.showAll:
					continue # ignore not installed packages
				else:
					icon = None
				store.append([icon, pkg])
		return store

	def load_session(self):
		try:
			self.session = Session("gtk_session.cfg")
		except (OSError, IOError), e:
			io_ex_dialog(e)
			raise

		def load_queue (merge, unmerge, oneshot):
			def _load(q, **kwargs):
				if q:
					for i in q.split(","):
						self.queue.append(i, **kwargs)

			_load(merge)
			_load(unmerge, unmerge = True)
			_load(oneshot, oneshot = True)
			
		def save_queue ():
			if self.__save_queue:
				return (",".join(self.queue.mergequeue), ",".join(self.queue.unmergequeue), ",".join(self.queue.oneshotmerge))
			else:
				return ("", "", "")

		map(self.session.add_handler,[
			([("width", "window"), ("height", "window")], lambda w,h: self.window.resize(int(w), int(h)), self.window.get_size),
			([("vpanedpos", "window")], lambda p: self.vpaned.set_position(int(p)), self.vpaned.get_position),
			([("merge", "queue"), ("unmerge", "queue"), ("oneshot", "queue")], load_queue, save_queue)
			])

		self.session.load()
	
	def jump_to (self, cp, version = None):
		"""Is called when we want to jump to a specific package."""
		self.show_package(cp, self.queue, version = version)

	def title_update (self, title):
		
		def window_title_update (title):
			if title is None or not self.cfg.get_boolean("updateTitle", "GUI"):
				self.window.set_title(self.main_title)
			else:
				title = title.strip()
				if title[0] == '*':
					self.window.set_title(self.main_title)
				else:
					space_idx = title.rfind(" ")
					if space_idx != -1:
						title = title[:space_idx]

					self.window.set_title(("Portato >>> %s" % title))

		def __update(title):
			if self.tray:
				self.tray.set_tooltip(title)
			
			window_title_update(title)
			if title is None: 
				title = _("Console")
			else: 
				title = (_("Console (%(title)s)") % {"title" : title})
			
			self.notebook.set_tab_label_text(self.termHB, title)

			return False

		gobject.idle_add(__update, title)

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

	def cb_pkg_list_selection (self, view):
		"""Callback for a package-list selection. Updates the package info."""
		sel = view.get_selection()
		store, it = sel.get_selected()
		if it:
			package = store.get_value(it, 1)
			self.show_package(self.selCatName+"/"+package, self.queue)
		return True

	def cb_pkg_list_header_clicked(self, col):
		self.sortPkgListByName = not self.sortPkgListByName
		self.pkgList.get_model().clear()
		self.fill_pkg_store(self.pkgList.get_model(), self.selCatName)
		return True

	def cb_row_activated (self, view, path, *args):
		"""Callback for an activated row in the emergeQueue. Opens a package window."""
		store = self.queueTree
		if len(path) > 1:
			iterator = store.get_original().get_iter(path)
			if store.iter_has_parent(iterator):
				package = store.get_value(iterator, store.get_cpv_column())
				cat, name, vers, rev = system.split_cpv(package)
				if rev != "r0": vers = vers+"-"+rev
				self.show_package(cat+"/"+name, queue = self.queue, version = vers, instantChange = True, doEmerge = False)
		return True
	
	def cb_queue_tooltip_queried (self, view, x, y, is_keyboard, tooltip):
		store = self.queueList.get_model()
		path = self.queueList.get_path_at_pos(x,y)

		if path is None:
			return False

		it = store.get_iter(path[0])

		if store.iter_parent(it) is None:
			return False # do not show tooltips for the root entries

		pkg = system.new_package(store.get_value(it, 0))
		
		enabled = []
		disabled = []
		expanded = set()

		pkg_flags = flags.sort_use_flag_list(pkg.get_iuse_flags(keep = True))
		if not pkg_flags: # no flags - stop here
			return None
		
		actual = pkg.get_actual_use_flags()
		
		if pkg.is_installed():
			installed = pkg.get_installed_use_flags()
		else:
			inst = system.find_installed_packages(pkg.get_slot_cp())
			if inst:
				installed = inst[0].get_installed_use_flags()
			else:
				installed = []

		for use in pkg_flags:
			if use.startswith(("+","-")):
				forced = (use[0] == "+")
				use = use[1:]
			else:
				forced = None

			exp = pkg.use_expanded(use)
			if exp:
				expanded.add(exp)
			
			else:
				useStr = use
				if installed and ((use in actual) != (use in installed)) and not (forced == (use in installed)):
					useStr += " %"
				if use in actual or forced:
					enabled.append(useStr)
				else:
					disabled.append(useStr)
		
		string = ""
		
		if enabled:
			string = "<b>+%s</b>" % ("\n+".join(enabled),)
			if len(disabled) > 0:
				string = string + "\n"
		
		if disabled:
			string = string+"<i>- %s</i>" % ("\n- ".join(disabled),)

		if expanded:
			string = string+"\n\n"+"\n".join(expanded)
		
		tooltip.set_markup(string)
		return string != ""

	def cb_emerge_clicked (self, action):
		"""Do emerge."""
		
		self.notebook.set_current_page(self.CONSOLE_PAGE)
		
		if len(flags.newUseFlags) > 0:
			changed_flags_dialog(_("use flags"))
			flags.write_use_flags()
		
		if len(flags.new_masked)>0 or len(flags.new_unmasked)>0 or len(flags.newTesting)>0:
			debug("new masked: %s",flags.new_masked)
			debug("new unmasked: %s", flags.new_unmasked)
			debug("new testing: %s", flags.newTesting)
			changed_flags_dialog(_("masking keywords"))
			flags.write_masked()
			flags.write_testing()
			system.reload_settings()
		
		if not self.doUpdate:
			self.queue.emerge(force=True)
		else:
			self.queue.update_world(force=True, newuse = self.cfg.get_boolean("newuse"), deep = self.cfg.get_boolean("deep"))
			self.doUpdate = False
		
	def cb_unmerge_clicked (self, button):
		"""Do unmerge."""

		self.notebook.set_current_page(self.CONSOLE_PAGE)
		self.queue.unmerge(force=True)
		return True

	def cb_update_clicked (self, action):
		def __update():
			
			def cb_idle_append (updating):
				try:
					try:
						for pkg, old_pkg in updating:
							self.queue.append(pkg.get_cpv(), unmask = False)
					except PackageNotFoundException, e:
						if unmask_dialog(e[0]) == gtk.RESPONSE_YES:
							for pkg, old_pkg in updating:
								self.queue.append(pkg.get_cpv(), unmask = True)

				except BlockedException, e:
					blocked_dialog(e[0], e[1])
					self.queue.remove_children(self.queue.emergeIt)
				
				return False

			watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
			self.window.window.set_cursor(watch)
			try:
				updating = system.update_world(newuse = self.cfg.get_boolean("newuse"), deep = self.cfg.get_boolean("deep"))
				debug("updating list: %s --> length: %s", [(x.get_cpv(), y.get_cpv()) for x,y in updating], len(updating))
				gobject.idle_add(cb_idle_append, updating)
				if len(updating): self.doUpdate = True
			finally:
				self.window.window.set_cursor(None)
			
		GtkThread(name="Update-Thread", target=__update).start()
		
		return True

	def cb_remove_clicked (self, button):
		"""Removes a selected item in the (un)emerge-queue if possible."""
		selected = self.queueList.get_selection()

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
				self.queue.remove_with_children(iter)
				self.doUpdate = False
		
		return True

	def cb_sync_clicked (self, action):
		self.notebook.set_current_page(self.CONSOLE_PAGE)
		cmd = self.cfg.get("syncCommand")

		if cmd != "emerge --sync":
			cmd = cmd.split()
			self.queue.sync(cmd)
		else:
			self.queue.sync()

	def cb_save_flags_clicked (self, action):
		flags.write_use_flags()
		flags.write_testing()
		flags.write_masked()

	@Window.watch_cursor
	def cb_reload_clicked (self, action):
		"""Reloads the portage settings and the database."""
		system.reload_settings()
		del self.db
		self.db = Database()
		self.db.populate()

	@Window.watch_cursor
	def cb_search_clicked (self, entry):
		"""Do a search."""
		text = entry.get_text()
		if text != "":
			if "/" not in text:
				text = "/.*"+text # only look for package names

			packages = system.find_all_packages(text, withVersion = False)

			if packages == []:
				nothing_found_dialog()
			else:
				if len(packages) == 1:
					self.jump_to(packages[0])
				else:
					SearchWindow(self.window, packages, self.jump_to)

	def cb_preferences_clicked (self, button):
		PreferenceWindow(self.window, self.cfg, self.console.set_font_from_string)
		return True

	def cb_about_clicked (self, button):
		AboutWindow(self.window)
		return True

	def cb_plugins_clicked (self, btn):
		queue = plugin.get_plugin_queue().get_plugins()
		if queue is None:
			queue = []
		
		PluginWindow(self.window, queue)
		return True
	
	def cb_show_updates_clicked (self, button):
		def __update():
			
			def cb_idle_show(packages):
				UpdateWindow(self.window, packages, self.queue, self.jump_to)
				return False
			
			watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
			self.window.window.set_cursor(watch)
			
			packages = []
			try:
				packages.extend(system.get_updated_packages())
			finally:
				self.window.window.set_cursor(None)

			gobject.idle_add(cb_idle_show, packages)
		
		GtkThread(name="Show Updates Thread", target = __update).start()
		return True

	def cb_show_installed_toggled (self, *args):
		self.showAll = not self.showAll

		store = self.catList.get_model()
		store.clear()
		self.fill_cat_store(store)

		store = self.pkgList.get_model()
		store.clear()
		try:
			self.fill_pkg_store(store, self.selCatName)
		except AttributeError: # no selCatName -> so no category selected --> ignore
			debug("AttributeError occured --> should be no harm.")

	def cb_right_click (self, object, event):
		if event.button == 3:
			x = int(event.x)
			y = int(event.y)
			time = event.time
			
			if object == self.queueList:
				pthinfo = object.get_path_at_pos(x, y)
				if pthinfo is not None:
					path, col, cellx, celly = pthinfo
					it = self.queueTree.get_original().get_iter(path)
					if self.queueTree.is_in_emerge(it) and self.queueTree.iter_has_parent(it):
						object.grab_focus()
						object.set_cursor(path, col, 0)
						self.queuePopup.popup(None, None, None, event.button, time)
					return True
			elif object == self.console:
				self.consolePopup.popup(None, None, None, event.button, time)
			else:
				return False
		else:
			return False

	def cb_oneshot_clicked (self, action):
		sel = self.queueList.get_selection()
		store, it = sel.get_selected()
		if it:
			package = store.get_value(it, 0)
			if not self.cfg.get_local(package, "oneshot"):
				set = True
			else:
				set = False
			
			self.cfg.set_local(package, "oneshot", set)
			self.queue.append(package, update = True, oneshot = set, forceUpdate = True)


	def cb_pause_emerge (self, curr):
		def pause (cb):
			self.emergePaused = cb.get_active()
			if not self.emergePaused:
				self.queue.continue_emerge()
			else:
				self.queue.stop_emerge()

			for v in self.pauseItems.itervalues():
				v[0].handler_block(v[1])

			for k, v in self.pauseItems.iteritems():
				if k != curr:
					v[0].set_active(self.emergePaused)

			for v in self.pauseItems.itervalues():
				v[0].handler_unblock(v[1])
			
			return False
		return pause

	def cb_kill_clicked (self, action):		
		self.queue.kill_emerge()
		if self.emergePaused:
			self.pauseItems["menu"][0].set_active(False)

	def cb_copy_clicked (self, action):
		self.console.copy_clipboard()

	def cb_delete (self, *args):
		"""Looks whether we really want to quit."""

		self.__save_queue = True

		if not self.queue.is_empty():
			ret = queue_not_empty_dialog()
			if ret == gtk.RESPONSE_CANCEL:
				return True
			else:
				self.__save_queue = (ret == gtk.RESPONSE_YES)
				self.queue.kill_emerge()

		# write session
		self.session.save()
		
		return False

	def cb_minimized (self, window, event):
		if self.tray and self.cfg.get_boolean("hideOnMinimize", "GUI"):
			if event.changed_mask & gtk.gdk.WINDOW_STATE_ICONIFIED:
				if event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED:
					self.window.hide()
					return True
		
		return False

	def cb_systray_activated (self, tray):
		if self.window.iconify_initially:
			self.window.deiconify()
			self.window.show()
			self.window.window.show()
		else:
			self.window.iconify()

	def cb_close (self, *args):
		if not self.cb_delete(): # do the checks
			self.window.destroy()

	def cb_destroy (self, widget):
		"""Calls main_quit()."""
		gtk.main_quit()
	
	def main (self):
		"""Main."""
		gobject.threads_init() 
		# now subthreads can run normally, but are not allowed to touch the GUI. If threads should change sth there - use gobject.idle_add().
		# for more informations on threading and gtk: http://www.async.com.br/faq/pygtk/index.py?req=show&file=faq20.006.htp
		gtk.main()
