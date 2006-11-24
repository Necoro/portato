# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/windows.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

# gtk stuff
import pygtk
pygtk.require("2.0")
import gtk
import gtk.glade
import gobject

#our backend stuff
from portato.helper import *
from portato.constants import CONFIG_LOCATION, VERSION, DATA_DIR
from portato import backend
from portato.backend import flags
from portato.backend.exceptions import *

# more GUI stuff
from portato.gui.gui_helper import Database, Config, EmergeQueue
from dialogs import *
from wrapper import GtkTree, GtkConsole

# for the terminal
import vte

# other
from portage_util import unique_array

class Window:
	def __init__ (self):
		self.tree = gtk.glade.XML(DATA_DIR+"portato.glade", root = self.__class__.__name__)
		self.tree.signal_autoconnect(self)
		self.window = self.tree.get_widget(self.__class__.__name__)

	@staticmethod
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

class AbstractDialog (Window):
	"""A class all our dialogs get derived from. It sets useful default vars and automatically handles the ESC-Button."""

	def __init__ (self, parent):
		"""Constructor.

		@param parent: the parent window
		@type parent: gtk.Window"""
		
		Window.__init__(self)

		# set parent
		self.window.set_transient_for(parent)
		
		# catch the ESC-key
		self.window.connect("key-press-event", self.cb_key_pressed)

	def cb_key_pressed (self, widget, event):
		"""Closes the window if ESC is pressed."""
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == "Escape":
			self.close()
			return True
		else:
			return False

	def close (self, *args):
		self.window.destroy()

class AboutWindow (AbstractDialog):
	"""A window showing the "about"-informations."""

	def __init__ (self, parent):
		"""Constructor.

		@param parent: the parent window
		@type parent: gtk.Window"""
		
		AbstractDialog.__init__(self, parent)

		label = self.tree.get_widget("aboutLabel")
		label.set_markup("""
<big><b>Portato v.%s</b></big>
A Portage-GUI
		
This software is licensed under the terms of the GPLv2.
Copyright (C) 2006 René 'Necoro' Neumann &lt;necoro@necoro.net&gt;

<small>Thanks to Fred for support and ideas :P</small>
""" % VERSION)

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
		
		AbstractDialog.__init__(self, parent)
		
		self.list = list # list to show
		self.jump_to = jump_to # function to call for jumping
		
		# combo box
		self.combo = gtk.combo_box_new_text()
		for x in list:
			self.combo.append_text(x)
		self.combo.set_active(0) # first item
		self.combo.connect("key-press-event", self.cb_key_pressed_combo)
		
		self.window.add(self.combo)

		# finished --> show
		self.window.show_all()

	def cb_key_pressed_combo (self, widget, event):
		"""Emulates a ok-button-click."""
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == "Return": # take it as an "OK" if Enter is pressed
			self.window.destroy()
			self.jump_to(self.list[self.combo.get_active()])
			return True
		else:
			return False

class PreferenceWindow (AbstractDialog):
	"""Window displaying some preferences."""
	
	# all checkboxes in the window
	# widget name -> option name
	checkboxes = {
			"debugCheck"			: "debug_opt",
			"deepCheck"				: "deep_opt",
			"newUseCheck"			: "newuse_opt",
			"maskPerVersionCheck"	: "maskPerVersion_opt",
			"usePerVersionCheck"	: "usePerVersion_opt",
			"testPerVersionCheck"	: "testingPerVersion_opt"
			}
	
	# all edits in the window
	# widget name -> option name
	edits = {
			"maskFileEdit"		: "maskFile_opt",
			"testFileEdit"		: "testingFile_opt",
			"useFileEdit"		: "useFile_opt",
			"syncCommandEdit"	: "syncCmd_opt"
			}

	def __init__ (self, parent, cfg):
		"""Constructor.

		@param parent: parent window
		@type parent: gtk.Window
		@param cfg: configuration object
		@type cfg: gui_helper.Config"""
		
		AbstractDialog.__init__(self, parent)

		# our config
		self.cfg = cfg
		
		# set the bg-color of the hint
		hintEB = self.tree.get_widget("hintEB")
		hintEB.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#f3f785"))

		for box in self.checkboxes:
			self.tree.get_widget(box).\
					set_active(self.cfg.get_boolean(self.checkboxes[box]))

		for edit in self.edits:
			self.tree.get_widget(edit).\
					set_text(self.cfg.get(self.edits[edit]))

		self.window.show_all()

	def _save(self):
		"""Sets all options in the Config-instance."""
		
		for box in self.checkboxes:
			self.cfg.set_boolean(self.checkboxes[box], self.tree.get_widget(box).get_active())

		for edit in self.edits:
			self.cfg.set(self.edits[edit],self.tree.get_widget(edit).get_text())
					
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
		
		# chechboxes
		self.installedCheck = self.tree.get_widget("installedCheck")
		self.maskedCheck = self.tree.get_widget("maskedCheck")
		self.testingCheck = self.tree.get_widget("testingCheck")

		# labels
		self.notInSysLabel = self.tree.get_widget("notInSysLabel")
		self.missingLabel = self.tree.get_widget("missingLabel")
		
		# buttons
		self.emergeBtn = self.tree.get_widget("pkgEmergeBtn")
		self.unmergeBtn = self.tree.get_widget("pkgUnmergeBtn")
		self.cancelBtn = self.tree.get_widget("pkgCancelBtn")
		
		# useList
		self.useListScroll = self.tree.get_widget("useListScroll")
		self.useList = None

	def update (self, cp, queue = None, version = None, doEmerge = True, instantChange = False):
		"""Updates the table to show the contents for the package.
		
		@param cp: the selected package
		@type cp: string (cp)
		@param queue: emerge-queue (if None the emerge-buttons are disabled)
		@type queue: EmergeQueue
		@param version: if not None, specifies the version to select
		@type version: string
		@param doEmerge: if False, the emerge buttons are disabled
		@type doEmerge: False
		@param instantChange: if True the changed keywords are updated instantly
		@type instantChange: boolean"""
		
		self.cp = cp # category/package
		self.version = version # version - if not None this is used
		self.queue = queue
		self.doEmerge = doEmerge
		self.instantChange = instantChange

		# packages and installed packages
		self.packages = backend.sort_package_list(backend.get_all_versions(cp))
		self.instPackages = backend.sort_package_list(backend.get_all_installed_versions(cp))

		# version-combo-box
		self.vCombo = self.build_vers_combo()
		if not self.doEmerge: self.vCombo.set_sensitive(False)
		vb = self.tree.get_widget("comboVB")
		children = vb.get_children()
		if children:
			for c in children: vb.remove(c)
		vb.pack_start(self.vCombo)

		# the label (must be here, because it depends on the combo box)
		desc = self.actual_package().get_env_var("DESCRIPTION").replace("&","&amp;")
		if not desc: 
			desc = "<no description>"
			use_markup = False
		else:
			desc = "<b>"+desc+"</b>"
			use_markup = True
		desc = "<i><u>"+self.actual_package().get_cp()+"</u></i>\n\n"+desc
		self.descLabel = self.tree.get_widget("descLabel")
		self.descLabel.set_use_markup(use_markup)
		self.descLabel.set_label(desc)
		
		if not self.queue or not self.doEmerge: 
			self.emergeBtn.set_sensitive(False)
			self.unmergeBtn.set_sensitive(False)
		
		# current status
		self.cb_combo_changed(self.vCombo)
		self.table.show_all()

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

	def _update_keywords (self, emerge, update = False):
		if emerge:
			try:
				try:
					self.queue.append(self.actual_package().get_cpv(), unmerge = False, update = update)
				except backend.PackageNotFoundException, e:
					if unmask_dialog(e[0]) == gtk.RESPONSE_YES:
						self.queue.append(self.actual_package().get_cpv(), unmerge = False, unmask = True, update = update)
			except BlockedException, e:
				blocked_dialog(e[0], e[1])
		else:
			try:
				self.queue.append(self.actual_package().get_cpv(), unmerge = True)
			except backend.PackageNotFoundException, e:
				masked_dialog(e[0])

	def cb_combo_changed (self, combo):
		"""Callback for the changed ComboBox.
		It then rebuilds the useList and the checkboxes."""
		
		# remove old useList
		w = self.useListScroll.get_child()
		if w:
			self.useListScroll.remove(w)
		
		# build new
		self.useList = self.build_use_list()
		self.useListScroll.add(self.useList)
		pkg = self.actual_package()
		
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
		else:
			self.missingLabel.hide()
			self.notInSysLabel.hide()
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
		
		self.table.show_all()

		return True

	def cb_button_pressed (self, b, event):
		"""Callback for pressed checkboxes. Just quits the event-loop - no redrawing."""
		if not isinstance(b, gtk.CellRendererToggle):
			b.emit_stop_by_name("button-press-event")
		return True

	def cb_package_revert_clicked (self, button):
		"""Callback for pressed cancel-button. Closes the window."""
		self.actual_package().remove_new_use_flags()
		self.actual_package().remove_new_masked()
		self.actual_package().remove_new_testing()
		self.cb_combo_changed(self.vCombo)
		if self.instantChange:
			self._update_keywords(True, update = True)
		return True

	def cb_package_emerge_clicked (self, button):
		"""Callback for pressed emerge-button. Adds the package to the EmergeQueue."""
		if not am_i_root():
			not_root_dialog()
		else:
			self._update_keywords(True)
			self.main.notebook.set_current_page(self.main.QUEUE_PAGE)
		return True

	def cb_package_unmerge_clicked (self, button):
		"""Callback for pressed unmerge-button clicked. Adds the package to the UnmergeQueue."""
		if not am_i_root():
			not_root_dialog()
		else:
			self._update_keywords(False)
			self.main.notebook.set_current_page(self.main.QUEUE_PAGE)
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

		if self.instantChange:
			self._update_keywords(True, update = True)
		
		return True

	def cb_masked_toggled (self, button):
		"""Callback for toggled masking-checkbox."""
		status = button.get_active()
		self.actual_package().set_masked(status)
		
		if self.instantChange:
			self._update_keywords(True, update = True)
		
		return True

	def cb_use_flag_toggled (self, cell, path, store):
		"""Callback for a toggled use-flag button."""
		store[path][0] = not store[path][0]
		prefix = ""
		if not store[path][0]:
			prefix = "-"
		self.actual_package().set_use_flag(prefix+store[path][1])
		
		if self.instantChange:
			self._update_keywords(True, update = True)
	
		return True

class MainWindow (Window):
	"""Application main window."""

	# NOTEBOOK PAGE CONSTANTS
	PKG_PAGE = 0
	QUEUE_PAGE = 1
	CONSOLE_PAGE = 2
	
	def __init__ (self):	
		"""Build up window"""

		# main window stuff
		Window.__init__(self)
		self.window.set_title(("Portato (%s)" % VERSION))
		mHeight = 800
		if gtk.gdk.screen_height() <= 800: mHeight = 600
		self.window.set_geometry_hints (self.window, min_width = 600, min_height = mHeight, max_height = gtk.gdk.screen_height(), max_width = gtk.gdk.screen_width())

		# booleans
		self.doUpdate = False
		self.packageInit = True
		
		# package db
		self.db = Database()
		self.db.populate()

		# config
		try:
			self.cfg = Config(CONFIG_LOCATION)
		except IOError, e:
			io_ex_dialog(e)
			raise e

		self.cfg.modify_external_configs()

		# set vpaned position
		vpaned = self.tree.get_widget("vpaned")
		vpaned.set_position(mHeight/2)

		# cat and pkg list
		self.catList = self.tree.get_widget("catList")
		self.pkgList = self.tree.get_widget("pkgList")
		self.build_cat_list()
		self.build_pkg_list()

		# queue list
		self.queueList = self.tree.get_widget("queueList")
		self.build_queue_list()

		# the terminal
		term = vte.Terminal()
		term.set_scrollback_lines(1024)
		term.set_scroll_on_output(True)
		term.set_font_from_string("Monospace 11")
		# XXX why is this not working with the colors
		term.set_color_background(gtk.gdk.color_parse("white"))
		term.set_color_foreground(gtk.gdk.color_parse("black"))
		termHB = self.tree.get_widget("termHB")
		termScroll = gtk.VScrollbar(term.get_adjustment())
		termHB.pack_start(term, True, True)
		termHB.pack_start(termScroll, False)
		
		# notebook
		self.notebook = self.tree.get_widget("notebook")
		self.window.show_all()
		
		# table
		self.packageTable = PackageTable(self)
		self.packageTable.table.hide_all()

		# popup
		popupTree = gtk.glade.XML(DATA_DIR+"portato.glade", root = "queuePopup")
		popupTree.signal_autoconnect(self)
		self.queuePopup = popupTree.get_widget("queuePopup")

		# set emerge queue
		self.queueTree = GtkTree(self.queueList.get_model())
		self.queue = EmergeQueue(console = GtkConsole(term), tree = self.queueTree, db = self.db)

	def show_package (self, *args, **kwargs):
		self.packageTable.update(*args, **kwargs)
		self.notebook.set_current_page(self.PKG_PAGE)

	def build_queue_list (self):
		"""Builds the queue list."""

		store = gtk.TreeStore(str,str)
		
		self.queueList.set_model(store)
		
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Queue", cell, text = 0)
		self.queueList.append_column(col)
		
		col = gtk.TreeViewColumn("Options", cell, markup = 1)
		self.queueList.append_column(col)

	def build_cat_list (self):
		"""Builds the category list."""
		
		store = gtk.ListStore(str)

		# build categories
		for p in backend.list_categories():
			store.append([p])
		# sort them alphabetically
		store.set_sort_column_id(0, gtk.SORT_ASCENDING)

		self.catList.set_model(store)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Categories", cell, text = 0)
		self.catList.append_column(col)

	def build_pkg_list (self, name = None):
		"""Builds the package list.
		
		@param name: name of the selected catetegory
		@type name: string"""
		
		store = gtk.ListStore(str)
		self.fill_pkg_store(store,name)
		
		# build view
		self.pkgList.set_model(store)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Packages", cell, text = 0)
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
			for p in self.db.get_cat(name):
				store.append([p])
		return store

	def jump_to (self, cp):
		"""Is called when we want to jump to a specific package."""
		self.show_package(cp, self.queue)

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
			package = store.get_value(it, 0)
			if package[-1] == '*': package = package[:-1]
			self.show_package(self.selCatName+"/"+package, self.queue)
		return True

	def cb_row_activated (self, view, path, *args):
		"""Callback for an activated row in the emergeQueue. Opens a package window."""
		store = self.queueTree
		if len(path) > 1:
			iterator = store.get_original().get_iter(path)
			if store.is_in_emerge(iterator):
				package = store.get_value(iterator, 0)
				cat, name, vers, rev = backend.split_package_name(package)
				if rev != "r0": vers = vers+"-"+rev
				self.show_package(cat+"/"+name, queue = self.queue, version = vers, instantChange = True, doEmerge = False)
		return True

	def cb_emerge_clicked (self, action):
		"""Do emerge."""
		
		self.notebook.set_current_page(self.CONSOLE_PAGE)
		
		if len(flags.newUseFlags) > 0:
			changed_flags_dialog("use flags")
			flags.write_use_flags()
		
		if len(flags.new_masked)>0 or len(flags.new_unmasked)>0 or len(flags.newTesting)>0:
			debug("new masked:",flags.new_masked)
			debug("new unmasked:", flags.new_unmasked)
			debug("new testing:", flags.newTesting)
			changed_flags_dialog("masking keywords")
			flags.write_masked()
			flags.write_testing()
			backend.reload_settings()
		
		if not self.doUpdate:
			self.queue.emerge(force=True)
		else:
			self.queue.update_world(force=True, newuse = self.cfg.get_boolean("newuse_opt"), deep = self.cfg.get_boolean("deep_opt"))
			self.doUpdate = False
		
	def cb_unmerge_clicked (self, button):
		"""Do unmerge."""

		self.notebook.set_current_page(self.CONSOLE_PAGE)
		self.queue.unmerge(force=True)
		return True

	@Window.watch_cursor
	def cb_update_clicked (self, action):
		if not backend.am_i_root():
			not_root_dialog()
		
		else:
			updating = backend.update_world(newuse = self.cfg.get_boolean("newuse_opt"), deep = self.cfg.get_boolean("deep_opt"))

			debug("updating list:", [(x.get_cpv(), y.get_cpv()) for x,y in updating])
			try:
				for pkg, old_pkg in updating:
					self.queue.append(pkg.get_cpv())
			except BlockedException, e:
				blocked_dialog(e[0], e[1])
			if len(updating): self.doUpdate = True
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
				self.queue.remove_children(iter) # remove children first
				self.queue.remove(iter)
				self.doUpdate = False
		
		return True

	def cb_sync_clicked (self, action):
		if not backend.am_i_root():
			not_root_dialog()
		else:
			self.notebook.set_current_page(self.CONSOLE_PAGE)
			cmd = self.cfg.get("syncCmd_opt")

			if cmd != "emerge --sync":
				cmd = cmd.split()
				self.queue.sync(cmd)
			else:
				self.queue.sync()

	def cb_save_flags_clicked (self, action):
		if not backend.am_i_root():
			not_root_dialog()
		else:
			flags.write_use_flags()
			flags.write_testing()
			flags.write_masked()
	
	@Window.watch_cursor
	def cb_reload_clicked (self, action):
		"""Reloads the portage settings and the database."""
		backend.reload_settings()
		del self.db
		self.db = Database()
		self.db.populate()

	@Window.watch_cursor
	def cb_search_clicked (self, entry):
		"""Do a search."""
		if entry.get_text() != "":
			packages = backend.find_all_packages(entry.get_text(), withVersion = False)

			if packages == []:
				nothing_found_dialog()
			else:
				if len(packages) == 1:
					self.jump_to(packages[0])
				else:
					SearchWindow(self.window, packages, self.jump_to)

	def cb_preferences_clicked (self, button):
		PreferenceWindow(self.window, self.cfg)
		return True

	def cb_about_clicked (self, button):
		AboutWindow(self.window)
		return True

	def cb_queue_right_click (self, queue, event):
		if event.button == 3:
			x = int(event.x)
			y = int(event.y)
			time = event.time
			pthinfo = queue.get_path_at_pos(x, y)
			if pthinfo is not None:
				path, col, cellx, celly = pthinfo
				if self.queueTree.is_in_emerge(self.queueTree.get_original().get_iter(path)):
					queue.grab_focus()
					queue.set_cursor(path, col, 0)
					self.queuePopup.popup(None, None, None, event.button, time)
				return True
			else:
				return False

	def cb_oneshot_clicked (self, action):
		sel = self.queueList.get_selection()
		store, it = sel.get_selected()
		if it:
			package = store.get_value(it, 0)
			if not self.cfg.get_local(package, "oneshot_opt"):
				set = True
			else:
				set = False
			
			self.cfg.set_local(package, "oneshot_opt", set)
			self.queue.append(package, update = True, oneshot = set, forceUpdate = True)
	
	def cb_destroy (self, widget):
		"""Calls main_quit()."""
		gtk.main_quit()
	
	def main (self):
		"""Main."""
		gobject.threads_init() 
		# now subthreads can run normally, but are not allowed to touch the GUI. If threads should change sth there - use gobject.idle_add().
		# for more informations on threading and gtk: http://www.async.com.br/faq/pygtk/index.py?req=show&file=faq20.006.htp
		gtk.main()