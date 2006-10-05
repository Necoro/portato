#
# File: geneticone/gui/windows.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 Necoro d.M.
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by Necoro d.M. <necoro@necoro.net>

# our backend stuff

VERSION = "0.3.4"
CONFIG_LOCATION = "/etc/geneticone/geneticone.cfg"
MENU_EMERGE = 1
MENU_UNEMERGE = 2

# gtk stuff
import pygtk
pygtk.require("2.0")
import gtk
import gobject

from geneticone.helper import *
from geneticone import backend
from geneticone.backend import flags
from gui_helper import *

# for the terminal
import pty
import vte

# other
from portage_util import unique_array

class AbstractDialog:

	def __init__ (self, parent, title):
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_title(title)
		self.window.set_modal(True)
		self.window.set_transient_for(parent)
		self.window.set_destroy_with_parent(True)
		self.window.set_resizable(False)
		self.window.set_default_size(1,1)
		self.window.connect("key-press-event", self.cb_key_pressed)

	def cb_key_pressed (self, widget, event):
		"""Closes the window if esc is pressed."""
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == "Escape":
			self.window.destroy()
			return True
		else:
			return False

class AboutWindow (AbstractDialog):
	"""A window showing the "about"-informations."""

	def __init__ (self, parent):
		AbstractDialog.__init__(self, parent, "About Genetic/One")
		box = gtk.VBox(False)
		self.window.add(box)
		
		label = gtk.Label()
		label.set_justify(gtk.JUSTIFY_CENTER)
		label.set_markup("""
<big><b>Genetic/One v.%s</b></big>
A Portage-GUI
		
This software is licensed under the terms of the GPLv2.
Copyright (C) 2006 Necoro d.M. &lt;necoro@necoro.net&gt;
""" % VERSION)
		box.pack_start(label)

		okBtn = gtk.Button("OK")
		okBtn.connect("clicked", lambda x: self.window.destroy())
		box.pack_start(okBtn)

		self.window.show_all()

class SearchWindow (AbstractDialog):
	"""A window showing the results of a search process."""
	
	def __init__ (self, parent, list, jump_to):
		AbstractDialog.__init__(self, parent, "Search results")
		
		self.list = list
		self.jump_to = jump_to

		box = gtk.HBox(False)
		self.window.add(box)

		self.combo = gtk.combo_box_new_text()
		for x in list:
			self.combo.append_text(x)
		self.combo.set_active(0)
		self.combo.connect("key-press-event", self.cb_key_pressed)

		box.pack_start(self.combo)

		okBtn = gtk.Button("OK")
		okBtn.connect("clicked", self.cb_ok_btn_clicked)
		box.pack_start(okBtn)

		self.window.show_all()

	def cb_ok_btn_clicked (self, button, data = None):
		self.window.destroy()
		self.jump_to(self.list[self.combo.get_active()])
		return True

	def cb_key_pressed (self, widget, event):
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == "Return": # take it as an "OK" if Enter is pressed
			self.cb_ok_btn_clicked(self,widget)
			return True
		elif keyname == "Escape":
			self.window.destroy()
			return True
		else:
			return False

class PreferenceWindow (AbstractDialog):

	def __init__ (self, parent, cfg):
		AbstractDialog.__init__(self, parent, "Preferences")

		self.cfg = cfg
		
		box = gtk.VBox(True)
		self.window.add(box)

		self.perVersionCb = gtk.CheckButton(label="Add to package.use on a per-version-base")
		self.perVersionCb.set_active(cfg.get_boolean(cfg.const["usePerVersion_opt"]))
		box.pack_start(self.perVersionCb, True, True)

		hBox = gtk.HBox()
		label = gtk.Label("File name to use if package.use is a directory:")
		self.editUsefile = gtk.Entry()
		self.editUsefile.set_text(cfg.get(cfg.const["useFile_opt"]))
		hBox.pack_start(label, False)
		hBox.pack_start(self.editUsefile, True, True, 5)
		box.pack_start(hBox, True, True)

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

		self.window.show_all()

	def _save(self):
		self.cfg.set(self.cfg.const["usePerVersion_opt"], str(self.perVersionCb.get_active()))
		self.cfg.set(self.cfg.const["useFile_opt"], self.editUsefile.get_text())

	def cb_ok_clicked(self, button):
		self._save()
		self.cfg.write()
		self.window.destroy()

class PackageWindow (AbstractDialog):
	"""A window with data about a specfic package."""

	def __init__ (self, parent, cp, queue = None, version = None, delOnClose = True, doEmerge = True):
		"""Build up window contents."""
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
		checkHB.pack_start(self.installedCheck, True, False)

		self.maskedCheck = gtk.CheckButton()
		self.maskedCheck.connect("button-press-event", self.cb_button_pressed)
		self.maskedCheck.set_label("Masked")		
		checkHB.pack_start(self.maskedCheck, True, False)

		self.testingCheck = gtk.CheckButton()
		self.testingCheck.connect("button-press-event", self.cb_button_pressed)
		self.testingCheck.set_label("Testing")
		checkHB.pack_start(self.testingCheck, True, False)

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
		if not self.queue or not doEmerge: 
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

	def update_checkboxes (self):
		"""Updates the checkboxes."""
		self.installedCheck.set_active(self.actual_package().is_installed())
		self.maskedCheck.set_active(self.actual_package().is_masked())
		self.testingCheck.set_active((self.actual_package().get_mask_status() % 3) == 1)

	def fill_use_list(self, store):
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
			combo.set_active(0)

		combo.connect("changed", self.cb_combo_changed)
		
		return combo

	def actual_package (self):
		"""Returns the actual package (a backend.Package-object)."""
		return self.packages[self.vCombo.get_active()]

	def cb_combo_changed (self, combo, data = None):
		"""Callback for the changed ComboBox.
		It then rebuilds the useList and the checkboxes."""
		
		store = self.useList.get_model()
		store.clear()
		self.fill_use_list(store)
		
		self.update_checkboxes()

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

	def cb_button_pressed (self, b, event, data = None):
		"""Callback for pressed checkboxes. Just quits the event-loop - no redrawing."""
		if not isinstance(b, gtk.CellRendererToggle):
			b.emit_stop_by_name("button-press-event")
		return True

	def cb_cancel_clicked (self, button, data = None):
		if self.delOnClose: 
			self.actual_package().remove_new_use_flags()
		elif self.flagChanged:
			if self.queue:
				self.queue.append(self.actual_package().get_cpv(), update = True)
		self.window.destroy()
		return True

	def cb_emerge_clicked (self, button, data = None):
		"""Adds the package to the EmergeQueue."""
		if not am_i_root():
			not_root_dialog()
		else:
			try:
				self.queue.append(self.actual_package().get_cpv(), unmerge = False)
			except backend.PackageNotFoundException, e:
				masked_dialog(e[0])
			self.window.destroy()
		return True

	def cb_unmerge_clicked (self, button, data = None):
		"""Adds the package to the UnmergeQueue."""
		if not am_i_root():
			not_root_dialog()
		else:
			try:
				self.queue.append(self.actual_package().get_cpv(), unmerge = True)
			except backend.PackageNotFoundException, e:
				masked_dialog(e[0])

			self.window.destroy()
		return True

	def cb_use_flag_toggled (self, cell, path, store, data = None):
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
		self.window.set_title("Genetic/One")
		self.window.connect("destroy", self.cb_destroy)
		self.window.set_border_width(2)
		self.window.set_geometry_hints (self.window, min_width = 600, min_height = 800, max_height = gtk.gdk.screen_height(), max_width = gtk.gdk.screen_width())
		self.window.set_resizable(True)

		# package db
		self.db = Database()
		self.db.populate()

		# config
		self.cfg = Config(CONFIG_LOCATION)
		self.cfg.modify_flags_config()

		# main vb
		vb = gtk.VBox(False, 1)
		self.window.add(vb)

		# menubar
		menubar = self.create_main_menu()
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
		vpaned.set_position(400)
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
		queueVB = gtk.VBox(False, 0)
		hb.pack_start(queueVB, True, True)
		
		queueScroll = gtk.ScrolledWindow()
		queueScroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		emergeStore = gtk.TreeStore(str)
		self.emergeView = gtk.TreeView(emergeStore)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Queue", cell, text = 0)
		self.emergeView.append_column(col)
		self.emergeView.connect("row-activated", self.cb_row_activated, emergeStore)
		queueScroll.add(self.emergeView)
		queueVB.pack_start(queueScroll, True, True)

		# buttons right unter the queue list
		buttonBox = gtk.HButtonBox()
		queueVB.pack_start(buttonBox, False)
		self.emergeBtn = gtk.Button("_Emerge")
		self.emergeBtn.connect("clicked", self.cb_emerge_clicked)
		self.unmergeBtn = gtk.Button("_Unmerge")
		self.unmergeBtn.connect("clicked", self.cb_emerge_clicked)
		self.removeBtn = gtk.Button("_Remove")
		self.removeBtn.connect("clicked", self.cb_remove_clicked)
		buttonBox.pack_start(self.emergeBtn)
		buttonBox.pack_start(self.removeBtn)
		buttonBox.pack_start(self.unmergeBtn)
		
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
		
		termFrame = gtk.Frame("Console")
		termFrame.set_shadow_type(gtk.SHADOW_IN)
		termFrame.add(termBox)
		vpaned.pack2(termFrame, shrink = True, resize = True)

		# the status line
		self.statusLabel = gtk.Label("Genetic/One - <Statusline>")
		self.statusLabel.set_alignment(0.0,0.7)
		self.statusLabel.set_single_line_mode(True)
		vb.pack_start(self.statusLabel, False, False)

		# show
		self.window.show_all()

		# set emerge queue
		self.queue = EmergeQueue(console=term, tree = emergeStore, db = self.db)

	def create_main_menu (self):
		"""Creates the main menu. XXX: Rebuild to use UIManager"""
		# the menu-list
		mainMenuDesc = [
				( "/_File", None, None, 0, "<Branch>"),
				( "/File/_Preferences", None, lambda x,y: PreferenceWindow(self.window, self.cfg), 0, ""),
				( "/File/", None, None, 0, "<Separator>"),
				( "/File/_Close", None, self.cb_destroy, 0, ""),
				( "/_Emerge", None, None, 0, "<Branch>"),
				( "/Emerge/_Emerge", None, self.cb_emerge_clicked, MENU_EMERGE, ""),
				( "/Emerge/_Unmerge", None, self.cb_emerge_clicked, MENU_UNEMERGE, ""),
				( "/_?", None, None, 0, "<Branch>"),
				( "/?/_About", None, lambda x,y: AboutWindow(self.window), 0, "")
				]
		self.itemFactory = gtk.ItemFactory(gtk.MenuBar, "<main>", None)
		self.itemFactory.create_items(mainMenuDesc)
		return self.itemFactory.get_widget("<main>")

	def fill_pkg_store (self, store, name = None):
		if name:
			for p in self.db.get_cat(name):
				store.append([p])
		return store
	
	def create_pkg_list (self, name = None, force = False):
		"""Creates the package list. Gets the name of the category."""
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
		"""Creates the category list."""
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

	def cb_cat_list_selection (self, view, data = None, force = False):
		"""Callback for a category-list selection. Updates the package list with these packages in the category."""
		if view == self.catList: # be sure it is the catList
			# get the selected category
			sel = view.get_selection()
			store, it = sel.get_selected()
			if it:
				self.selCatName = store.get_value(it, 0)
				self.pkgList.get_model().clear()
				self.fill_pkg_store(self.pkgList.get_model(), self.selCatName)
		return False

	def cb_row_activated (self, view, path, col, store = None):
		"""Callback for an activated row in the pkgList. Opens a package window."""
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

	def cb_remove_clicked (self, button, data = None):
		"""Removes a selected item in the (un)emerge-queue if possible."""
		selected = self.emergeView.get_selection()

		if selected:
			model, iter = selected.get_selected()

			if not model.iter_parent(iter): # top-level
				if model.iter_n_children(iter) > 0: # and has children which can be removed :)
					askMB = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you really want to clear the whole queue?")
					if askMB.run() == gtk.RESPONSE_YES :
						self.queue.remove_children(iter)
					askMB.destroy()
			elif model.iter_parent(model.iter_parent(iter)): # this is in the 3rd level => dependency
				infoMB = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "You cannot remove dependencies. :)")
				infoMB.run()
				infoMB.destroy()
			else:
				self.queue.remove(iter)
		
		return True

	def cb_emerge_clicked (self, button, data = None):
		"""Do emerge or unemerge."""
		if button == self.emergeBtn or button == MENU_EMERGE:
			if len(flags.newUseFlags) > 0:
				hintMB = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK,
						"You have changed use flags. Genetic/One will write these changes into the appropriate files. Please backup them if you think it is necessairy.")
				hintMB.run()
				hintMB.destroy()
				flags.write_use_flags()
			self.queue.emerge(force=True)
		elif button == self.unmergeBtn or button == MENU_UNEMERGE:
			self.queue.unmerge(force=True)

		return True

	def cb_search_clicked (self, button, data = None):
		"""Do a search."""
		if self.searchEntry.get_text() != "":
			packages = backend.find_all_packages(self.searchEntry.get_text(), withVersion = False)

			if packages == []:
				dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "Package not found!")
				dialog.run()
				dialog.destroy()
			else:
				if len(packages) == 1:
					self.jump_to(packages[0])
				else:
					SearchWindow(self.window, packages, self.jump_to)

	def main (self):
		"""Main."""
		gobject.threads_init() 
		# now subthreads can run normally, but are not allowed to touch the GUI. If threads should change sth there - use gobject.idle_add().
		# for more informations on threading and gtk: http://www.async.com.br/faq/pygtk/index.py?req=show&file=faq20.006.htp
		gtk.main()

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
