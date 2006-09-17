#!/usr/bin/python

# our backend stuff
import geneticone

# gtk stuff
import pygtk
pygtk.require("2.0")
import gtk
import gobject

# for doing emerge
from subprocess import *

# threading
from threading import Thread

# for the terminal
import pty
import vte

# other
from portage_util import unique_array

class EmergeQueue:
	"""This class manages the emerge queue."""

	def __init__ (self, tree = None, console = None, packages = None):
		""""tree" is a gtk.TreeStore to show the queue in; "console" is a vte.Terminal to print the output to."""
		self.mergequeue = {}
		self.unmergequeue = []
		self.tree = tree
		self.console = console
		self.packages = packages

		if self.tree:
			self.emergeIt = self.tree.append(None, ["Emerge"])
			self.unmergeIt = self.tree.append(None, ["Unmerge"])
		else:
			self.emergeIt = self.unmergeIt = None

	def append (self, sth, unmerge = False):
		"""Appends a cpv either to the merge queue or to the unmerge-queue.
		Also update the tree-view."""
		if not unmerge:
			# insert dependencies
			pkg = geneticone.find_packages("="+sth)[0]
			try:
				self.mergequeue.update({sth : pkg.get_dep_packages()})
			except geneticone.BlockedException, e :
				blocks = e[0]
				blocked_dialog(sth, blocks)
				return
			else:
				# update tree
				if self.emergeIt:
					pkgIt = self.tree.append(self.emergeIt, [sth])
					for p in self.mergequeue[sth]:
						self.tree.append(pkgIt, [p])
		else:
			self.unmergequeue.append(sth)
			if self.unmergeIt: # update tree
				self.tree.append(self.unmergeIt, [sth])
	
	def update_packages(self, process, packages):
		"""This updates the packages-list. It simply removes all affected categories so they have to be rebuilt."""
		process.wait()
		for p in packages:
			try:
				cat = geneticone.split_package_name(p)[0]
				while cat[0] in ["=",">","<","!"]:
					cat = cat[1:]
				print cat
				del self.packages[cat]
				print "deleted"
			except KeyError:
				pass

	def _emerge (self, options, packages, it):
		"""Calls emerge and updates the terminal."""
		(master, slave) = pty.openpty()
		self.console.set_pty(master)
		process = Popen(["/usr/bin/python","/usr/bin/emerge"]+options+packages, stdout = slave, stderr = STDOUT, shell = False)
		Thread(target=self.update_packages, args=(process, packages)).start()
		self.remove_all(it)

	def emerge (self, force = False):
		"""Emerges everything in the merge-queue. If force is 'False' (default) only 'emerge -pv' is called."""
		if len(self.mergequeue) == 0: return

		list = []
		for k in self.mergequeue.keys():
			list += ["="+k]
		
		s = []
		if not force: s = ["-pv"]
		self._emerge(s,list, self.emergeIt)

	def unmerge (self, force = False):
		"""Unmerges everything in the umerge-queue. If force is 'False' (default) only "emerge -pv -C" is called."""
		if len(self.unmergequeue) == 0: return

		list = self.unmergequeue[:]
		s = ["-C"]
		if not force: s = ["-Cpv"]
		self._emerge(s,list, self.unmergeIt)

	def remove_all (self, parentIt):
		"""Removes all children of a given parent TreeIter."""
		childIt = self.tree.iter_children(parentIt)

		while childIt:
			temp = childIt
			childIt = self.tree.iter_next(childIt)
			self.remove(temp)
	
	def remove (self, it):
		"""Removes a specific item in the tree."""
		if self.tree.iter_parent(it): # NEVER remove our top stuff
			if self.tree.get_string_from_iter(it).split(":")[0] == self.tree.get_string_from_iter(self.emergeIt):
				del self.mergequeue[self.tree.get_value(it,0)]
			else:
				self.unmergequeue.remove(self.tree.get_value(it,0))
			
			self.tree.remove(it)

class PackageWindow:
	"""A window with data about a specfic package."""

	def cb_changed (self, combo, data = None):
		"""Callback for the changed ComboBox.
		It then rebuilds the useList and the checkboxes."""
		# remove old useList
		self.useListScroll.remove(self.useList)
		
		# build new
		self.useList = self.build_use_list()
		self.useListScroll.add(self.useList)
		self.update_checkboxes()

		self.useListScroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)

		# set emerge-button-label
		if not self.actual_package().is_installed():
			self.emergeBtn.set_label("_Emerge")
		else:
			self.emergeBtn.set_label("_Unmerge")
		
		# refresh - make window as small as possible
		self.table.show_all()
		self.window.resize(1,1)
		return True

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
				best_version = geneticone.find_best_match(self.packages[0].get_cp(), (self.instPackages != [])).get_version()
			for i in range(len(self.packages)):
				if self.packages[i].get_version() == best_version:
					combo.set_active(i)
					break
		except AttributeError: # no package found
			combo.set_active(0)

		combo.connect("changed", self.cb_changed)
		
		return combo

	def actual_package (self):
		"""Returns the actual package (a geneticone.Package-object)."""
		return self.packages[self.vCombo.get_active()]

	def cb_button_pressed (self, b, event, data = None):
		"""Callback for pressed checkboxes. Just quits the event-loop - no redrawing."""
		b.emit_stop_by_name("button-press-event")
		return True

	def cb_emerge_clicked (self, button, data = None):
		"""Adds the package to the EmergeQueue."""
		if not geneticone.am_i_root():
			errorMB = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "You cannot (un)merge without being root.")
			errorMB.run()
			errorMB.destroy()
		else:
			unmerge = self.actual_package().is_installed()
			self.queue.append(self.actual_package().get_cpv(), unmerge)
			self.window.destroy()
		return True

	def update_checkboxes (self):
		"""Updates the checkboxes."""
		self.installedCheck.set_active(self.actual_package().is_installed())
		self.maskedCheck.set_active(self.actual_package().is_masked())
		self.testingCheck.set_active((self.actual_package().get_mask_status() % 3) == 1)

	def build_use_list (self):
		"""Builds the useList."""
		store = gtk.ListStore(bool, str, str)

		pkg = self.actual_package()
		for use in pkg.get_all_useflags():
			if pkg.is_installed() and use in pkg.get_set_useflags(): # flags set during install
				enabled = True
			elif (not pkg.is_installed()) and use in pkg.get_settings("USE").split(): # flags that would be set
				enabled = True
			else:
				enabled = False
			store.append([enabled, use, geneticone.get_use_desc(use, self.cp)])

		# build view
		view = gtk.TreeView(store)
		cell = gtk.CellRendererText()
		tCell = gtk.CellRendererToggle()
		view.append_column(gtk.TreeViewColumn("Enabled", tCell, active = 0))
		view.append_column(gtk.TreeViewColumn("Flags", cell, text = 1))
		view.append_column(gtk.TreeViewColumn("Description", cell, text = 2))

		if store.iter_n_children(None) == 0:
			view.set_child_visible(False)
		else:
			view.set_child_visible(True)
		return view

	def __init__ (self, parent, cp, queue = None, version = None):
		"""Build up window contents."""
		self.parent = parent # parent window
		self.cp = cp # category/package
		self.version = version # version - if not None this is used
		self.queue = queue
		
		# window
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_title(cp)
		self.window.set_modal(True)
		self.window.set_transient_for(parent)
		self.window.set_destroy_with_parent(True)
		self.window.set_resizable(False)
		self.window.set_default_size(1,1) # as small as possible
		self.window.connect("delete-event", lambda a,b: False)
		#self.window.connect("configure-event", self.cbSizeCheck)
		
		# packages and installed packages
		self.packages = geneticone.sort_package_list(geneticone.find_packages(cp, masked=True))
		self.instPackages = geneticone.sort_package_list(geneticone.find_installed_packages(cp, masked=True))

		# main structure - the table
		self.table = gtk.Table(rows=4,columns=2)
		self.window.add(self.table)

		# version-combo-box
		self.vCombo = self.build_vers_combo()
		self.table.attach(self.vCombo, 0, 1, 1, 2, yoptions = gtk.FILL)

		# the label (must be here, because it depends on the combo box)
		desc = self.actual_package().get_env_var("DESCRIPTION")
		use_markup = True
		if not desc: 
			desc = "<no description>"
			use_markup = False
		else:
			desc = "<b>"+desc+"</b>"
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
		if not self.queue: self.emergeBtn.set_sensitive(False)
		self.cancelBtn = gtk.Button("_Cancel")
		self.cancelBtn.connect("clicked", lambda x: self.window.destroy())
		self.emergeBtn.connect("clicked", self.cb_emerge_clicked)
		buttonHB.pack_start(self.emergeBtn)
		buttonHB.pack_start(self.cancelBtn)

		# current status
		self.cb_changed(self.vCombo)

		# show
		self.window.show_all()

class SearchWindow:
	"""A window showing the results of a search process."""
	def cb_ok_btn_clicked (self, button, data = None):
		self.window.destroy()
		self.jump_to(self.list[self.combo.get_active()])
	
	def __init__ (self, parent, list, jump_to):
		# window
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_title("Search results")
		self.window.set_modal(True)
		self.window.set_transient_for(parent)
		self.window.set_destroy_with_parent(True)
		self.window.set_resizable(False)
		self.window.set_default_size(1,1)
		self.list = list
		self.jump_to = jump_to

		box = gtk.HBox(False)
		self.window.add(box)

		self.combo = gtk.combo_box_new_text()
		for x in list:
			self.combo.append_text(x)
		self.combo.set_active(0)

		box.pack_start(self.combo)

		okBtn = gtk.Button("OK")
		okBtn.connect("clicked", self.cb_ok_btn_clicked)
		box.pack_start(okBtn)

		self.window.show_all()


class MainWindow:
	"""Application main window."""
	
	def cb_delete (self, widget, data = None):
		"""Returns false -> window is deleted."""
		return False

	def cb_destroy (self, widget, data = None):
		"""Calls main_quit()."""
		gtk.main_quit()

	def create_main_menu (self):
		"""Creates the main menu. XXX: Rebuild to use UIManager"""
		# the menu-list
		mainMenuDesc = [
				( "/_File", None, None, 0, "<Branch>"),
				( "/File/_Close", None, self.cb_destroy, 0, ""),
				( "/_Emerge", None, None, 0, "<Branch>"),
				( "/Emerge/_Emerge", None, self.cb_emerge_clicked, 0, ""),
				( "/Emerge/_Unmerge", None, self.cb_emerge_clicked, 0, ""),
				( "/_?", None, None, 0, "<Branch>"),
				( "/?/_About", None, None, 0, "")
				]
		self.itemFactory = gtk.ItemFactory(gtk.MenuBar, "<main>", None)
		self.itemFactory.create_items(mainMenuDesc)
		return self.itemFactory.get_widget("<main>")

	def cb_cat_list_selection (self, view, data = None, force = False):
		"""Callback for a category-list selection. Updates the package list with these packages in the category."""
		if view == self.catList: # be sure it is the catList
			# get the selected category
			sel = view.get_selection()
			store, it = sel.get_selected()
			
			if it:
				# remove old one
				self.scroll_2.remove(self.pkgList)
				# create new package list
				self.pkgList = self.create_pkg_list(store.get_value(it,0), force)
				self.scroll_2.add(self.pkgList)
				self.scroll_2.show_all()
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
				cat, name, vers, rev = geneticone.split_package_name(package)
				PackageWindow(self.window, cat+"/"+name, queue = None, version = vers+"-"+rev)
		return True

	def create_cat_list (self):
		"""Creates the category list."""
		store = gtk.ListStore(str)

		# build categories
		for p in geneticone.list_categories():
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

	packages = {} # directory category -> [packages]
	def create_pkg_list (self, name = None, force = False):
		"""Creates the package list. Gets the name of the category."""
		self.selCatName = name # actual category
		store = gtk.ListStore(str)

		# calculate packages
		if name:
			if name not in self.packages and not force: # only calc packages if not already done
				self.packages[name] = []
				for p in unique_array([x.get_name() for x in geneticone.find_all_packages(name+"/")]):
					if geneticone.find_installed_packages(name+"/"+p, masked=True) != []:
						p += "*" # append a '*' if the package is installed
					self.packages[name].append(p)

			for p in self.packages[name]:
				store.append([p])

			# sort alphabetically
			store.set_sort_column_id(0, gtk.SORT_ASCENDING)

		# build view
		pkgList = gtk.TreeView(store)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Packages", cell, text = 0)
		pkgList.append_column(col)
		pkgList.connect("row-activated", self.cb_row_activated, store)

		return pkgList

	def cb_remove_clicked (self, button, data = None):
		"""Removes a selected item in the (un)emerge-queue if possible."""
		selected = self.emergeView.get_selection()

		if selected:
			model, iter = selected.get_selected()

			if not model.iter_parent(iter): # top-level
				if model.iter_n_children(iter) > 0: # and has children which can be removed :)
					askMB = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you really want to clear the whole queue?")
					if askMB.run() == gtk.RESPONSE_YES :
						self.queue.remove_all(iter)
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
		if button == self.emergeBtn:
			self.queue.emerge(force=True)
		elif button == self.unmergeBtn:
			self.queue.unmerge(force=True)

		return True

	def cb_search_clicked (self, button, data = None):
		"""Do a search."""
		if self.searchEntry.get_text() != "":
			packages = geneticone.find_all_packages(self.searchEntry.get_text())

			if packages == []:
				dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "Package not found!")
				dialog.run()
				dialog.destroy()
			else:
				packages = unique_array([p.get_cp() for p in packages])
				
				if len(packages) == 1:
					self.jump_to(packages[0])
				else:
					SearchWindow(self.window, packages, self.jump_to)

	def jump_to (self, cp):
		"""Is called when we want to jump to a specific package."""
		PackageWindow(self.window, cp, self.queue)

	def __init__ (self):
		"""Build up window"""

		# window
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_title("Genetic/One")
		self.window.connect("delete_event", self.cb_delete)
		self.window.connect("destroy", self.cb_destroy)
		self.window.set_border_width(2)
		self.window.set_geometry_hints (self.window, min_width = 600, min_height = 800, max_height = gtk.gdk.screen_height(), max_width = gtk.gdk.screen_width())
		self.window.set_resizable(True)

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
		
		emergeStore = gtk.TreeStore(str)
		self.emergeView = gtk.TreeView(emergeStore)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Queue", cell, text = 0)
		self.emergeView.append_column(col)
		self.emergeView.connect("row-activated", self.cb_row_activated, emergeStore)
		queueVB.pack_start(self.emergeView, True, True)

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

		# show
		self.window.show_all()

		# set emerge queue
		self.queue = EmergeQueue(console=term, tree = emergeStore, packages = self.packages)
	
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
