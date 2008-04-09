# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/main.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2008 René 'Necoro' Neumann
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
import itertools as itt

# our backend stuff
from ...backend import flags, system # must be the first to avoid circular deps
from ... import get_listener, plugin, dependency
from ...helper import debug, warning, error, info, unique_array
from ...session import Session
from ...constants import CONFIG_LOCATION, VERSION, APP_ICON
from ...backend.exceptions import PackageNotFoundException, BlockedException

# more GUI stuff
from ..utils import Database, Config
from ..queue import EmergeQueue
from ..session import SESSION_VERSION, SessionException, OldSessionException, NewSessionException
from ..wrapper import GtkTree, GtkConsole
from ..exception_handling import GtkThread
from ..views import LogView, HighlightView, InstalledOnlyView
from ..dialogs import (blocked_dialog, changed_flags_dialog, io_ex_dialog,
		nothing_found_dialog, queue_not_empty_dialog, remove_deps_dialog,
		remove_queue_dialog, remove_updates_dialog, unmask_dialog)

# even more GUI stuff
from .basic import Window, Popup
from .about import AboutWindow
from .plugin import PluginWindow
from .preference import PreferenceWindow
from .search import SearchWindow
from .update import UpdateWindow

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
		
		# all the package data is in this one VB
		self.vb = self.tree.get_widget("packageVB")

		# the notebook
		self.notebook = self.tree.get_widget("packageNotebook")
		
		# the version combo
		self.versionList = self.tree.get_widget("versionList")
		self.build_version_list()

		# chechboxes
		self.installedCheck = self.tree.get_widget("installedCheck")
		self.maskedCheck = self.tree.get_widget("maskedCheck")
		self.testingCheck = self.tree.get_widget("testingCheck")
		self.maskedLabel = self.tree.get_widget("maskedLabel")

		# labels
		generalVB = self.tree.get_widget("generalVB")
		generalVB.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
		
		self.nameLabel = self.tree.get_widget("nameLabel")
		self.descLabel = self.tree.get_widget("descLabel")
		self.overlayLabel = self.tree.get_widget("overlayLabel")
		self.overlayLL = self.tree.get_widget("overlayLabelLabel")
		self.licenseLabel = self.tree.get_widget("licenseLabel")
		self.linkBox = self.tree.get_widget("linkBox")
		self.notInSysLabel = self.tree.get_widget("notInSysLabel")
		self.missingLabel = self.tree.get_widget("missingLabel")
		self.useFlagsLabel = self.tree.get_widget("useFlagsLabel")
		self.useFlagsLL = self.tree.get_widget("useFlagsLabelLabel")
		
		# buttons
		self.emergeBtn = self.tree.get_widget("pkgEmergeBtn")
		self.unmergeBtn = self.tree.get_widget("pkgUnmergeBtn")
		self.revertBtn = self.tree.get_widget("pkgRevertBtn")
		
		# useList
		self.useList = self.tree.get_widget("useList")
		self.build_use_list()

		# depList
		self.depList = self.tree.get_widget("dependencyList")
		self.build_dep_list()

		# views
		self.ebuildView = self.tree.get_widget("ebuildScroll").get_child()
		self.changelogView = self.tree.get_widget("changelogScroll").get_child()
		self.filesView = self.tree.get_widget("filesScroll").get_child()

		# icons
		self.icons = {}
		self.icons["use"] = self.window.render_icon(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
		self.icons["installed"] = self.window.render_icon(gtk.STOCK_YES, gtk.ICON_SIZE_MENU)
		self.icons["or"] = self.window.render_icon(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_MENU)
		self.icons["block"] = self.window.render_icon(gtk.STOCK_NO, gtk.ICON_SIZE_MENU)

	def update (self, cp, queue = None, version = None, doEmerge = True, instantChange = False, type = None):
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
		@type instantChange: boolean
		@param type: the type of the queue this package is in; if None there is no queue :)
		@type type: string"""
		
		self.cp = cp # category/package
		self.version = version # version - if not None this is used
		self.queue = queue
		self.doEmerge = doEmerge
		self.instantChange = instantChange
		self.type = type

		# packages and installed packages
		if not self.doEmerge:
			self.instPackages = self.packages = system.find_packages("=%s-%s" % (cp, version), masked = True)
		else:
			self.packages = system.sort_package_list(system.find_packages(cp, masked = True))
			self.instPackages = system.sort_package_list(system.find_installed_packages(cp, masked = True))

		# version-combo-box
		self.versionList.get_model().clear()
		self.fill_version_list()

		if not self.queue or not self.doEmerge: 
			self.emergeBtn.set_sensitive(False)
			self.unmergeBtn.set_sensitive(False)
		
		# current status
		self.cb_version_list_changed()
		self.vb.show_all()

	def hide (self):
		self.vb.hide_all()

	def set_labels (self):
		pkg = self.actual_package()
		
		# name
		self.nameLabel.set_markup("<b>%s</b>" % pkg.get_cp())
		
		# description
		desc = pkg.get_package_settings("DESCRIPTION") or _("<no description>")
		self.descLabel.set_label(desc)

		# overlay
		if pkg.is_overlay():
			self.overlayLabel.set_label(pkg.get_overlay_path())
			self.overlayLabel.show()
			self.overlayLL.show()
		else:
			self.overlayLabel.hide()
			self.overlayLL.hide()

		# license
		self.licenseLabel.set_label(pkg.get_package_settings("LICENSE"))

		# link
		for c in self.linkBox.get_children():
			self.linkBox.remove(c)
		
		text = pkg.get_package_settings("HOMEPAGE")
		texts = text.split(" ")
		ftexts = []

		for count, t in enumerate(texts):
			if not t.startswith(("http", "ftp")):
				if count == 0:
					error(_("The first homepage part does not start with 'http' or 'ftp'."))
					ftexts.append(t)
					continue
				else:
					info(_("Blank inside homepage."))
					ftexts[-1] += " %s" % t
			else:
				ftexts.append(t)

		for t in ftexts:
			link = gtk.LinkButton(t)
			link.set_alignment(0.0, 0.5)
			link.set_border_width(0)
			self.linkBox.add(link)

		# useflags
		flaglist = list(itt.ifilterfalse(pkg.use_expanded, pkg.get_iuse_flags()))
		flaglist.sort()
		flags = ", ".join(flaglist)

		if flags:
			self.useFlagsLL.show()
			self.useFlagsLabel.show()
			self.useFlagsLabel.set_label(flags)
		else:
			self.useFlagsLL.hide()
			self.useFlagsLabel.hide()

	def fill_dep_list(self):

		store = self.depList.get_model()
				
		def add (tree, it):

			def get_icon (dep):
				if dep.satisfied:
					return self.icons["installed"]
				elif dep.dep[0] == "!":
					return self.icons["block"]
				else:
					return None

			# useflags
			for use, usetree in tree.flags.iteritems():
				if use[0] == "!":
					usestring = _("If '%s' is disabled") % use[1:]
				else:
					usestring = _("If '%s' is enabled") % use
				useit = store.append(it, [self.icons["use"], usestring])
				add(usetree, useit)
			
			# ORs
			ordeps = (dep for dep in tree.deps if isinstance(dep, dependency.OrDependency))

			for ordep in ordeps:
				orit = store.append(it, [self.icons["or"], _("One of the following")])

				for dep in ordep.dep:
					if isinstance(dep, dependency.AllOfDependency): # a list inside or
						allit = store.append(orit, [None, _("All of the following")])
						for adep in dep.dep:
							store.append(allit, [get_icon(adep), adep.dep])
					else:
						store.append(orit, [get_icon(dep), dep.dep])
			
			# normal
			def sort_key (x):
				split = system.split_cpv(x.dep)

				if split is None: # split_cpv returns None if this is only a CP; we assume there are only valid deps
					return x.dep
				else:
					return "/".join(split[0:2])
			
			ndeps = [dep for dep in tree.deps if not isinstance(dep, dependency.OrDependency)]
			ndeps.sort(key = sort_key)
			for dep in ndeps:
				store.append(it, [get_icon(dep), dep.dep])
		
		try:
			deptree = self.actual_package().get_dependencies()
		except AssertionError:
			w =  _("Can't display dependencies: This package has an unsupported dependency string.")
			error(w)
			store.append(None, [None, w])
		else:
			add(deptree, None)

	def fill_use_list(self):

		pkg = self.actual_package()
		pkg_flags = pkg.get_iuse_flags()
		pkg_flags.sort()
	
		actual_exp = None
		actual_exp_it = None

		euse = pkg.get_actual_use_flags()
		instuse = pkg.get_installed_use_flags()

		store = self.useList.get_model()

		for use in pkg_flags:
			exp = pkg.use_expanded(use, suggest = actual_exp)
			if exp is not None:
				if exp != actual_exp:
					actual_exp_it = store.append(None, [None, None, exp, "<i>%s</i>" % _("This is an expanded use flag and cannot be selected")])
					actual_exp = exp
			else:
				actual_exp_it = None
				actual_exp = None

			enabled = use in euse
			installed = use in instuse
			store.append(actual_exp_it, [enabled, installed, use, system.get_use_desc(use, self.cp)])
		
	def build_dep_list (self):
		store = gtk.TreeStore(gtk.gdk.Pixbuf, str)

		self.depList.set_model(store)

		col = gtk.TreeViewColumn()

		cell = gtk.CellRendererPixbuf()
		col.pack_start(cell, False)
		col.add_attribute(cell, "pixbuf", 0)

		cell = gtk.CellRendererText()
		col.pack_start(cell, True)
		col.add_attribute(cell, "text", 1)

		self.depList.append_column(col)
	
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

	def build_version_list (self):
		store = gtk.ListStore(gtk.gdk.Pixbuf, str, str)

		# build view
		self.versionList.set_model(store)
		
		col = gtk.TreeViewColumn(_("Versions"))
		col.set_property("expand", True)
		
		self.slotcol = gtk.TreeViewColumn(_("Slot"))
		self.slotcol.set_property("expand", True)

		# adding the pixbuf
		cell = gtk.CellRendererPixbuf()
		col.pack_start(cell, False)
		col.add_attribute(cell, "pixbuf", 0)

		# adding the package name
		cell = gtk.CellRendererText()
		col.pack_start(cell, True)
		col.add_attribute(cell, "text", 1)

		# adding the slot
		cell = gtk.CellRendererText()
		self.slotcol.pack_start(cell, True)
		self.slotcol.add_attribute(cell, "text", 2)

		self.versionList.append_column(col)
		self.versionList.append_column(self.slotcol)

	def fill_version_list (self):
		
		store = self.versionList.get_model()

		# this is here for performance reasons
		# to not query the package with info, we do not need
		if self.main.cfg.get_boolean("showSlots", "GUI"):
			def get_slot(pkg):
				return pkg.get_package_settings("SLOT")
			
			self.slotcol.set_visible(True)
		
		else:
			def get_slot(*args):
				return ""
			
			self.slotcol.set_visible(False)
		
		# append versions
		for vers, inst, slot in ((x.get_version(), x.is_installed(), get_slot(x)) for x in self.packages):
			if inst:
				icon = self.main.instPixbuf
			else:
				icon = None
				
			store.append([icon, vers, slot])

		pos = ((0,)) # default
		
		# activate the first one
		try:
			best_version = ""
			if self.version:
				best_version = self.version
			else:
				best_version = system.find_best_match(self.packages[0].get_cp(), only_installed = (self.instPackages != [])).get_version()
			for i in range(len(self.packages)):
				if self.packages[i].get_version() == best_version:
					pos = (i,)
					break
		except AttributeError: # no package found
			pass

		self.versionList.get_selection().select_path(pos)
		self.versionList.scroll_to_cell(pos)

	def actual_package (self):
		"""Returns the actual selected package.
		
		@returns: the actual selected package
		@rtype: backend.Package"""

		model, iter = self.versionList.get_selection().get_selected()
		if iter:
			return self.packages[model.get_path(iter)[0]]
		else:
			return self.packages[0]

	def _update_keywords (self, emerge, update = False):
		if emerge:
			type = "install" if not self.type else self.type
			try:
				try:
					self.queue.append(self.actual_package().get_cpv(), type = type, update = update)
				except PackageNotFoundException, e:
					if unmask_dialog(e[0]) == gtk.RESPONSE_YES:
						self.queue.append(self.actual_package().get_cpv(), type = type, unmask = True, update = update)
			except BlockedException, e:
				blocked_dialog(e[0], e[1])
		else:
			try:
				self.queue.append(self.actual_package().get_cpv(), type = "uninstall")
			except PackageNotFoundException, e:
				error(_("Package could not be found: %s"), e[0])
				#masked_dialog(e[0])

	def cb_version_list_changed (self, *args):

		pkg = self.actual_package()

		# set the views
		for v in (self.ebuildView, self.changelogView, self.filesView):
			v.update(pkg, force = self.notebook.get_nth_page(self.notebook.get_current_page()) == v.get_parent())

		# set the labels
		self.set_labels()

		# set use list
		self.useList.get_model().clear()
		self.useList.columns_autosize()
		self.fill_use_list()

		# set dep list
		self.depList.get_model().clear()
		self.useList.columns_autosize()
		self.fill_dep_list()
		
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
#			
			self.installedCheck.hide()
			self.maskedCheck.hide()
			self.maskedLabel.hide()
			self.testingCheck.hide()
			self.emergeBtn.set_sensitive(False)
		else: # normal package
			self.missingLabel.hide()
			self.notInSysLabel.hide()
			self.installedCheck.show()
			self.maskedCheck.show()
			self.maskedLabel.show()
			self.testingCheck.show()
			if self.doEmerge:
				self.emergeBtn.set_sensitive(True)
			self.installedCheck.set_active(pkg.is_installed())
			
			reason = pkg.get_masking_reason() or " "
			if pkg.is_masked(use_changed = False) and not pkg.is_masked(use_changed = True):
				self.maskedCheck.set_label("<i>(%s)</i>" % _("Masked"))
				self.maskedCheck.get_child().set_use_markup(True)
			else:
				self.maskedCheck.set_label(_("Masked"))
			
			if pkg.is_locally_masked():
				self.maskedCheck.set_label("<b>%s</b>" % _("Masked"))
				self.maskedCheck.get_child().set_use_markup(True)
				self.maskedCheck.set_active(True)
				reason = _("Masked by user")
			else:
				self.maskedCheck.set_active(pkg.is_masked(use_changed = False))
			
			if reason:
				self.maskedLabel.set_label(reason)
			
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
		
		self.vb.show_all()
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
		self.versionList.get_model().clear()
		self.fill_version_list()
		self.cb_version_list_changed()
		if self.instantChange:
			self._update_keywords(True, update = True)
		return True

	def cb_package_emerge_clicked (self, button):
		"""Callback for pressed emerge-button. Adds the package to the EmergeQueue."""
		self._update_keywords(True)
		self.main.sysNotebook.set_current_page(self.main.QUEUE_PAGE)
		return True

	def cb_package_unmerge_clicked (self, button):
		"""Callback for pressed unmerge-button clicked. Adds the package to the UnmergeQueue."""
		self._update_keywords(False)
		self.main.sysNotebook.set_current_page(self.main.QUEUE_PAGE)
		return True

	def cb_testing_toggled (self, button):
		"""Callback for toggled testing-checkbox."""
		status = button.get_active()

		# end of recursion :)
		if self.actual_package().is_testing(use_keywords = False) == status:
			return False

		# if the package is not testing - don't allow to set it as such
		if not self.actual_package().is_testing(use_keywords = False):
			button.set_active(False)
			return True

		# re-set to testing status
		if not self.actual_package().is_testing(use_keywords = True):
			self.actual_package().set_testing(False)
			button.set_label(_("Testing"))
			button.set_active(True)
		else: # disable testing
			self.actual_package().set_testing(True)
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
				self.maskedLabel.set_label(_("Masked by user"))
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
				self.maskedLabel.set_label("")
		
		if self.instantChange:
			self._update_keywords(True, update = True)
		
		return True

	def cb_use_flag_toggled (self, cell, path, store):
		"""Callback for a toggled use-flag button."""
		flag = store[path][2]
		pkg = self.actual_package()
		
		if pkg.use_expanded(flag): # ignore expanded flags
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
	"""
	Application main window.
	"""

	# NOTEBOOK PAGE CONSTANTS
	(
			QUEUE_PAGE,
			CONSOLE_PAGE,
			LOG_PAGE
	) = range(3)

	def __init__ (self, splash = None):	
		"""
		Build up window.

		@param splash: the splash screen =)
		@type splash: SplashScreen
		"""

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
		self.__searchChanged = False

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
		self.set_uri_hook(self.cfg.get("browserCmd", section = "GUI"))
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
		# set paned position
		self.vpaned = self.tree.get_widget("vpaned")
		self.vpaned.set_position(int(self.window.get_size()[1]/2))
		self.hpaned = self.tree.get_widget("hpaned")
		self.hpaned.set_position(int(self.window.get_size()[0]/1.5))

		# cat and pkg list
		self.sortPkgListByName = True
		self.catList = self.tree.get_widget("catList")
		self.pkgList = self.tree.get_widget("pkgList")
		self.build_cat_list()
		self.build_pkg_list()

		# search entry
		self.searchEntry = self.tree.get_widget("searchEntry")

		# queue list
		self.queueList = self.tree.get_widget("queueList")
		self.build_queue_list()

		# the terminal
		self.console = GtkConsole()
		self.termHB = self.tree.get_widget("termHB")
		self.build_terminal()
		
		# notebooks
		self.sysNotebook = self.tree.get_widget("systemNotebook")
		self.pkgNotebook = self.tree.get_widget("packageNotebook")
		self.set_notebook_tabpos(map(PreferenceWindow.tabpos.get, map(int, (self.cfg.get("packageTabPos", "GUI"), self.cfg.get("systemTabPos", "GUI")))))
		
		# the different scrolls
		ebuildScroll = self.tree.get_widget("ebuildScroll")
		ebuildScroll.add(HighlightView(lambda p: p.get_ebuild_path(), ["gentoo", "sh"]))

		changelogScroll = self.tree.get_widget("changelogScroll")
		changelogScroll.add(HighlightView(lambda p: os.path.join(p.get_package_path(), "ChangeLog"), ["changelog"]))

		def show_files (p):
			try:
				for f in p.get_files():
					yield " %s\n" % f
			except IOError, e:
				yield _("Error: %s") % e.strerror

		filesScroll = self.tree.get_widget("filesScroll")
		filesScroll.add(InstalledOnlyView(show_files))
		
		# table
		self.packageTable = PackageTable(self)

		# popups
		self.queuePopup = Popup("queuePopup", self, self.__file__)
		self.consolePopup = Popup("consolePopup", self, self.__file__)
		self.trayPopup = Popup("systrayPopup", self)

		# pause menu items
		self.emergePaused = False
		self.pauseItems = {}
		self.pauseItems["tray"] = self.trayPopup.tree.get_widget("pauseItemTray")
		self.pauseItems["popup"] = self.consolePopup.tree.get_widget("pauseItemPopup")
		self.pauseItems["menu"] = self.tree.get_widget("pauseItemMenu")

		for k,v in self.pauseItems.iteritems():
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
		
		self.catList.get_selection().select_path(1)
		self.pkgList.get_selection().select_path(0)
		
		# session
		splash(_("Restoring Session"))
		try:
			try:
				self.load_session()
			except OldSessionException, e:
				self.load_session(e)
		except SessionException, e:
			warning(str(e))
		
		splash(_("Finishing startup"))
		
		self.window.show_all()
	
	def show_package (self, *args, **kwargs):
		self.packageTable.update(*args, **kwargs)

	def build_terminal (self):
		"""
		Builds the terminal.
		"""
		
		self.console.set_scrollback_lines(1024)
		self.console.set_scroll_on_output(True)
		self.console.set_font_from_string(self.cfg.get("consolefont", "GUI"))
		self.console.connect("button-press-event", self.cb_right_click)
		self.termHB.pack_start(self.console, True, True)
		
		# add scrollbar
		termScroll = gtk.VScrollbar(self.console.get_adjustment())
		self.termHB.pack_start(termScroll, False)

	def build_queue_list (self):
		"""
		Builds the queue list.
		"""

		store = gtk.TreeStore(str,str,bool)
		
		self.queueList.set_model(store)
		
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn(_("Queue"), cell, markup = 0)
		self.queueList.append_column(col)
		
		col = gtk.TreeViewColumn(_("Options"), cell, markup = 1)
		self.queueList.append_column(col)

	def build_cat_list (self):
		"""
		Builds the category list.
		"""
		
		store = gtk.ListStore(str)

		self.catList.set_model(store)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn(_("Categories"), cell, text = 0)
		self.catList.append_column(col)

		self.fill_cat_store(store)
		self.catList.get_selection().connect("changed", self.cb_cat_list_selection)

	def fill_cat_store (self, store):
		"""
		Fills the category store with data.

		@param store: the store to fill
		@type store: gtk.ListStore
		"""

		cats = self.db.get_categories(installed = not self.showAll)

		for p in cats:
			store.append([p])
		
		# sort them alphabetically
		store.set_sort_column_id(0, gtk.SORT_ASCENDING)

	def build_pkg_list (self, name = None):
		"""
		Builds the package list.
		
		@param name: name of the selected catetegory
		@type name: string
		"""
		
		store = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
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

		self.pkgList.get_selection().connect("changed", self.cb_pkg_list_selection)

	def fill_pkg_store (self, store, name = None):
		"""
		Fills a given ListStore with the packages in a category.
		
		@param store: the store to fill
		@type store: gtk.ListStore
		@param name: the name of the category
		@type name: string
		"""

		if name:
			for cat, pkg, is_inst in self.db.get_cat(name, self.sortPkgListByName):
				if is_inst:
					icon = self.instPixbuf
				elif not self.showAll:
					continue # ignore not installed packages
				else:
					icon = None
				store.append([icon, pkg, cat])

	def refresh_stores (self):
		"""
		Refreshes the category and package stores.
		"""
		store = self.catList.get_model()
		store.clear()
		self.fill_cat_store(store)

		store = self.pkgList.get_model()
		store.clear()
		try:
			self.fill_pkg_store(store, self.selCatName)
		except AttributeError: # no selCatName -> so no category selected --> ignore
			debug("No category selected --> should be no harm.")

	def load_session(self, sessionEx = None):
		"""
		Loads the session data.
		"""
		try:
			self.session = Session("gtk_session.cfg")
		except (OSError, IOError), e:
			io_ex_dialog(e)
			return

		oldVersion = SESSION_VERSION
		allowedVersions = (0,1)

		if sessionEx and isinstance(sessionEx, SessionException):
			if sessionEx.got in allowedVersions:
				info(_("Translating session from version %d to %d.") % (sessionEx.got, sessionEx.expected))
				oldVersion = sessionEx.got
			else:
				warning(_("Cannot translate session from version %d to %d.") % (sessionEx.got, sessionEx.expected))
				raise sessionEx

		#
		# the callbacks for the different session variables
		#

		# QUEUE
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

		# PANED
		def load_paned (*pos):
			pos = map(int, pos)
			[x.set_position(p) for x,p in zip((self.vpaned, self.hpaned), pos)]

		def save_paned ():
			return [x.get_position() for x in (self.vpaned, self.hpaned)]

		# SELECTION
		def load_selection (list, col):
			def _load (name):
				pos = "0" # default
				
				if name:
					for cname, path in ((x[col], x.path) for x in list.get_model()):
						if cname == name:
							pos = path
				
				list.get_selection().select_path(pos)
				list.scroll_to_cell(pos)
			
			return _load

		def save_pkg_selection ():
			store, iter = self.pkgList.get_selection().get_selected()
			if iter:
				return store.get_value(iter, 1)
			else:
				return ""

		def save_cat_selection ():
			# try to find the correct category using the pkgList selection
			# so we do not select ALL =)
			# if no package has been selected - return selCatName
			store, iter = self.pkgList.get_selection().get_selected()
			if iter:
				return store.get_value(iter, 2)
			else:
				return self.selCatName

		# PLUGIN
		def load_plugin (p):
			def _load(val):
				if val:
					p.status = int(val)*2

			return _load
		
		def save_plugin (p):
			def _save ():
				stat_on = p.status >= p.STAT_ENABLED
				hard_on = not p.get_option("disabled")

				if stat_on != hard_on:
					return int(stat_on)
				else:
					return ""
			return _save

		# SESSION VERSION
		def load_session_version (version):
			if oldVersion != SESSION_VERSION: # we are trying to convert
				return
			
			version = int(version)

			if version < SESSION_VERSION:
				raise OldSessionException(version, SESSION_VERSION)
			elif version > SESSION_VERSION:
				raise NewSessionException(version, SESSION_VERSION)

		# set the simple ones :)
		map(self.session.add_handler,[
			([("gtksessionversion", "session")], load_session_version, lambda: SESSION_VERSION),
			([("width", "window"), ("height", "window")], lambda w,h: self.window.resize(int(w), int(h)), self.window.get_size),
			([("vpanedpos", "window"), ("hpanedpos", "window")], load_paned, save_paned),
			([("catsel", "window")], load_selection(self.catList, 0), save_cat_selection),
			([("pkgsel", "window")], load_selection(self.pkgList, 1), save_pkg_selection)
			#([("merge", "queue"), ("unmerge", "queue"), ("oneshot", "queue")], load_queue, save_queue),
			])

		# set the plugins
		queue = plugin.get_plugin_queue()
		if queue:
			for p in queue.get_plugins():
				self.session.add_handler(([(p.name.replace(" ","_"), "plugins")], load_plugin(p), save_plugin(p)))

		# now we have the handlers -> load
		self.session.load()
	
	def jump_to (self, cp, version = None):
		"""
		Is called when we want to jump to a specific package.

		@param cp: the CP to jump to
		@type cp: string
		@param version: if not None jump to a specific version
		@type version: string
		"""

		cat, pkg = cp.split("/")

		for list, idx, what, expr in ((self.catList, 0, "categories", cat), (self.pkgList, 1, "packages", pkg)):
			pathes = [row.path for row in list.get_model() if row[idx] == expr]

			if len(pathes) == 1:
				list.get_selection().select_path(pathes[0])
				list.scroll_to_cell(pathes[0])
			else:
				debug("Unexpected number of %s returned after search: %d", what, len(pathes))
				break

		self.show_package(cp, self.queue, version = version)

	def set_uri_hook (self, browser):
		"""
		Sets the browser command which is called when a URL is going to be opened.

		@param browser: the browser command
		@type browser: string
		"""

		browser = browser.split()
		gtk.link_button_set_uri_hook(lambda btn, x: get_listener().send_cmd(browser+[btn.get_uri()]))

	def set_notebook_tabpos (self, tabposlist):
		"""
		Sets the positions of the tabs of the notebooks.

		@param tabposlist: the list of positions: first comes the one for package tabs; sndly for sys tabs
		@type tabposlist: int[]
		"""
		self.pkgNotebook.set_tab_pos(tabposlist[0])
		self.sysNotebook.set_tab_pos(tabposlist[1])

	def title_update (self, title):
		"""
		Updates the titles of the window and the systray.
		Mainly used with emerge term titles.

		@param title: the title
		@type title: string
		"""
		
		def window_title_update (title):
			"""
			Updates the title of the main window.
			"""
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
			if title is None or not self.cfg.get_boolean("updateConsole", "GUI"): 
				title = _("Console")
			else: 
				title = ("%s (%s)") % (_("Console"), title)
			
			self.sysNotebook.set_tab_label_text(self.termHB, title)

			return False

		# as this might get called from other threads use gobject.idle_add
		gobject.idle_add(__update, title)

	def cb_cat_list_selection (self, selection):
		"""
		Callback for a category-list selection. 
		Updates the package list with the packages in the category.
		"""
		# get the selected category
		store, it = selection.get_selected()
		if it:
			self.selCatName = store.get_value(it, 0)
			self.pkgList.get_model().clear()
			self.fill_pkg_store(self.pkgList.get_model(), self.selCatName)
		return True

	def cb_pkg_list_selection (self, selection):
		"""
		Callback for a package-list selection.
		Updates the package info.
		"""
		store, it = selection.get_selected()
		if it:
			cp = "%s/%s" % (store.get_value(it, 2), store.get_value(it, 1))
			self.show_package(cp, self.queue)
		return True

	def cb_pkg_list_header_clicked(self, col):
		self.sortPkgListByName = not self.sortPkgListByName
		self.pkgList.get_model().clear()
		self.fill_pkg_store(self.pkgList.get_model(), self.selCatName)
		return True

	def cb_queue_row_activated (self, view, path, *args):
		"""Callback for an activated row in the emergeQueue. Opens a package window."""
		store = self.queueTree
		if len(path) > 1:
			iterator = store.get_original().get_iter(path)
			if store.iter_has_parent(iterator):
				package = store.get_value(iterator, store.get_cpv_column())
				cat, name, vers, rev = system.split_cpv(package)
				if rev != "r0": vers = vers+"-"+rev

				if store.is_in_emerge(iterator):
					type = "install"
				elif store.is_in_unmerge(iterator):
					type = "uninstall"
				elif store.is_in_update(iterator):
					type = "update"

				self.show_package(cat+"/"+name, queue = self.queue, version = vers, instantChange = True, doEmerge = False, type = type)
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

		pkg_flags = pkg.get_iuse_flags()
		pkg_flags.sort()
		if not pkg_flags: # no flags - stop here
			return None
		
		actual = set(pkg.get_actual_use_flags())
		
		if pkg.is_installed():
			installed = set(pkg.get_iuse_flags()).intersection(pkg.get_installed_use_flags())
		else:
			inst = system.find_installed_packages(pkg.get_slot_cp())
			if inst:
				installed = set(inst[0].get_iuse_flags()).intersection(inst[0].get_installed_use_flags())
			else:
				installed = set()

		diff = actual.symmetric_difference(installed)

		for use in pkg_flags:
			exp = pkg.use_expanded(use)
			if exp:
				expanded.add(exp)
			
			else:
				useStr = use
				if installed and use in diff:
					useStr += " %"
				if use in actual:
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

	def cb_execute_clicked (self, action):
		"""Execute the current queue."""
		
		if len(flags.newUseFlags) > 0:
			changed_flags_dialog(_("use flags"))
			try:
				flags.write_use_flags()
			except IOError, e:
				io_ex_dialog(e)
				return True
		
		if len(flags.new_masked)>0 or len(flags.new_unmasked)>0 or len(flags.newTesting)>0:
			debug("new masked: %s",flags.new_masked)
			debug("new unmasked: %s", flags.new_unmasked)
			debug("new testing: %s", flags.newTesting)
			changed_flags_dialog(_("masking keywords"))
			try:
				flags.write_masked()
				flags.write_testing()
			except IOError, e:
				io_ex_dialog(e)
				return True
			else:
				system.reload_settings()

		model, iter = self.queueList.get_selection().get_selected()

		if iter is None:
			if model.iter_n_children(None) == 1: # only one queue there - take this as being selected
				iter = model.get_iter_root()
			else:
				return False

		self.sysNotebook.set_current_page(self.CONSOLE_PAGE)
		
		# test which type of queue we have here
		if self.queueTree.is_in_emerge(iter):
			self.queue.emerge(force = True)
		elif self.queueTree.is_in_unmerge(iter):
			self.queue.unmerge(force = True)
		else:
			self.queue.update_world(force=True, newuse = self.cfg.get_boolean("newuse"), deep = self.cfg.get_boolean("deep"))

		return True
		
	def cb_update_clicked (self, action):
		def __update():
			
			def cb_idle_append (updating):
				try:
					try:
						for pkg, old_pkg in updating:
							self.queue.append(pkg.get_cpv(), type = "update", unmask = False)
					except PackageNotFoundException, e:
						if unmask_dialog(e[0]) == gtk.RESPONSE_YES:
							for pkg, old_pkg in updating:
								self.queue.append(pkg.get_cpv(), type = "update", unmask = True)

				except BlockedException, e:
					blocked_dialog(e[0], e[1])
					self.queue.remove_children(self.queueTree.get_update_it())
				
				return False

			watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
			self.window.window.set_cursor(watch)
			try:
				updating = system.update_world(newuse = self.cfg.get_boolean("newuse"), deep = self.cfg.get_boolean("deep"))
				debug("updating list: %s --> length: %s", [(x.get_cpv(), y.get_cpv()) for x,y in updating], len(updating))
				gobject.idle_add(cb_idle_append, updating)
			finally:
				self.window.window.set_cursor(None)
			
		GtkThread(name="Update-Thread", target=__update).start()
		
		return True

	def cb_remove_clicked (self, button):
		"""Removes a selected item in the (un)emerge-queue if possible."""
		model, iter = self.queueList.get_selection().get_selected()

		if iter:
			parent = model.iter_parent(iter)
			
			if self.queueTree.is_in_update(iter) and parent:
				if remove_updates_dialog() == gtk.RESPONSE_YES:
					self.queue.remove_with_children(self.queueTree.get_update_it())
			
			elif not parent: # top-level
				if model.iter_n_children(iter) > 0: # and has children which can be removed :)
					if remove_queue_dialog() == gtk.RESPONSE_YES :
						self.queue.remove_with_children(iter)
				else:
					self.queue.remove(iter)
			
			elif model.iter_parent(parent): # this is in the 3rd level => dependency
				remove_deps_dialog()
			else:
				self.queue.remove_with_children(iter)

				if model.iter_n_children(parent) == 0: # no more children left - remove queue too
					self.queue.remove(parent)
		
			return True
		return False

	def cb_sync_clicked (self, action):
		self.sysNotebook.set_current_page(self.CONSOLE_PAGE)
		cmd = self.cfg.get("syncCommand")

		if cmd != "emerge --sync":
			cmd = cmd.split()
			self.queue.sync(cmd)
		else:
			self.queue.sync()

	def cb_save_flags_clicked (self, action):
		try:
			flags.write_use_flags()
			flags.write_testing()
			flags.write_masked()
		except IOError, e:
			io_ex_dialog(e)

	@Window.watch_cursor
	def cb_reload_clicked (self, action):
		"""Reloads the portage settings and the database."""
		system.reload_settings()
		self.db.reload()

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

		return True

	def cb_search_changed (self, *args):
		"""
		Called when the user enters something in the search field.
		Updates the packages according to the search expression.
		"""
		if not self.__searchChanged and self.cfg.get_boolean("searchOnType", section="GUI"):
			self.__searchChanged = True
			
			def __update():
				self.__searchChanged = False
				txt = self.searchEntry.get_text()

				if txt or self.db.restrict:
					self.db.restrict = txt

				self.refresh_stores()
				self.catList.get_selection().select_path("0") # XXX make this smarter

				return False # not again ;)

			gobject.timeout_add(100, __update)

	def cb_delete_search_clicked (self, *args):
		self.searchEntry.set_text("")
		return True

	def cb_preferences_clicked (self, *args):
		"""
		User wants to open preferences.
		"""
		PreferenceWindow(self.window, self.cfg, self.console.set_font_from_string, self.set_uri_hook, self.set_notebook_tabpos)
		return True

	def cb_about_clicked (self, *args):
		"""
		User wants to open about dialog.
		"""
		AboutWindow(self.window)
		return True

	def cb_plugins_clicked (self, *args):
		"""
		User wants to open plugin dialog.
		"""
		queue = plugin.get_plugin_queue()
		if queue is None:
			plugins = []
		else:
			plugins = queue.get_plugins()
		
		PluginWindow(self.window, plugins)
		return True
	
	def cb_show_updates_clicked (self, *args):
		"""
		Show the list of updateble packages.
		"""

		def __update():			
			def cb_idle_show(packages):
				"""
				Callback opening the menu when the calculation is finished.

				@returns: False to signal that it is finished
				"""
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
		"""
		Toggle the "show only installed" option.
		"""
		self.showAll = not self.showAll
		self.refresh_stores()

	def cb_right_click (self, object, event):
		"""
		Called when the user right clicks somewhere.
		Used to display a menu.
		
		This method should handle ALL such menus.

		@param object: the object/widget where the click is done
		@type object: gtk.Widget
		@param event: the event triggered
		@type event: gtk.gdk.Event
		"""

		if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3: # 3 == right click
			x = int(event.x)
			y = int(event.y)
			time = event.time
			
			if object == self.queueList:
				pthinfo = object.get_path_at_pos(x, y)
				if pthinfo is not None:
					path, col, cellx, celly = pthinfo
					it = self.queueList.get_model().get_iter(path)
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

	def cb_oneshot_clicked (self, *args):
		"""
		Mark a package as oneshot.
		"""
		sel = self.queueList.get_selection()
		store, it = sel.get_selected()
		if it:
			package = store.get_value(it, 0)
			set = (package not in self.queue.oneshotmerge)
			
			self.queue.append(package, update = True, oneshot = set, forceUpdate = True)

	def cb_pause_emerge (self, curr):
		"""
		This method returns a callback for a "pause emerge" toggle button.
		It is needed as there are different toggle buttons of this type and if one is clicked,
		the others should be marked too.

		@param curr: The button to return the callback for.
		@type curr: gtk.ToggleButton
		"""
		def pause (cb):
			"""
			The actual callback.

			Mark all other buttons too.

			@param cb: The button which got toggled.
			@type cb: gtk.ToggleButton
			"""

			# pause or continue
			self.emergePaused = cb.get_active()
			if not self.emergePaused:
				self.queue.continue_emerge()
			else:
				self.queue.stop_emerge()

			# block the handlers of the other buttons
			# so that calling "set_active" does not call this callback recursivly
			for v in self.pauseItems.itervalues():
				v[0].handler_block(v[1])

			# mark the others
			for k, v in self.pauseItems.iteritems():
				if k != curr:
					v[0].set_active(self.emergePaused)

			# unblock
			for v in self.pauseItems.itervalues():
				v[0].handler_unblock(v[1])
			
			return False
		return pause

	def cb_kill_clicked (self, *args):
		"""
		Kill emerge.
		"""
		self.queue.kill_emerge()
		if self.emergePaused: # unmark the "pause emerge" buttons
			self.pauseItems["menu"][0].set_active(False) # calling one button is enough (see: cb_pause_emerge)

	def cb_copy_clicked (self, *args):
		"""
		Copy marked text in the terminal to clipboard.
		"""
		self.console.copy_clipboard()

	def cb_delete (self, *args):
		"""
		Called when the user wants to quit the application.

		Asks the user for confirmation if there is something in the queue.
		Also saves session data.
		"""

		self.__save_queue = False

		if not self.queue.is_empty():
			ret = queue_not_empty_dialog()
			if ret == gtk.RESPONSE_CANCEL:
				return True
			else: # there is sth in queue AND the user still wants to close -> kill emerge
				self.__save_queue = (ret == gtk.RESPONSE_YES)
				self.queue.kill_emerge()

		# write session
		self.session.save()
		
		return False

	def cb_minimized (self, window, event):
		"""
		User wants to minimize the window. 
		If it is possible to minimize to tray, it is done.
		"""

		if self.tray and self.cfg.get_boolean("hideOnMinimize", "GUI"):
			if event.changed_mask & gtk.gdk.WINDOW_STATE_ICONIFIED:
				if event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED:
					self.window.hide()
					return True
		
		return False

	def cb_systray_activated (self, *args):
		"""
		Systray was activated. Show or hide the window.
		"""
		if self.window.iconify_initially:
			self.window.deiconify()
			self.window.show()
			self.window.window.show()
		else:
			self.window.iconify()

	def cb_close (self, *args):
		"""
		"Close" menu entry called.
		Emulate normal quitting.
		"""
		if not self.cb_delete(): # do the checks
			self.window.destroy()

	def cb_destroy (self, *args):
		"""
		Calls main_quit().
		"""
		gtk.main_quit()
	
	def main (self):
		"""
		Main.
		"""
		gobject.threads_init()
		# now subthreads can run normally, but are not allowed to touch the GUI. If threads should change sth there - use gobject.idle_add().
		# for more informations on threading and gtk: http://www.async.com.br/faq/pygtk/index.py?req=show&file=faq20.006.htp
		plugin.hook("main")(gtk.main)()
