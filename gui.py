#!/usr/bin/python

import geneticone

import pygtk
pygtk.require("2.0")
import gtk

# for doing emerge
from subprocess import *

# for the terminal
import pty
import vte

from portage_util import unique_array

class EmergeQueue:
	"""This class manages the emerge queue."""

	def __init__ (self, tree = None, console = None):
		""""tree" is a gtk.TreeStore to show the queue in; "console" is a vte.Terminal to print the output to."""
		self.mergequeue = {}
		self.unmergequeue = []
		self.tree = tree
		self.console = console

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
				blockedDialog(sth, blocks)
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

	def _emerge (self, options, it):
		"""Calls emerge and updates the terminal."""
		# open pty
		(master, slave) = pty.openpty()
		Popen("emerge "+options, stdout = slave, stderr = STDOUT, shell = True)
		self.removeAll(it)
		self.console.set_pty(master)

	def emerge (self, force = False):
		"""Emerges everything in the merge-queue. If force is 'False' (default) only 'emerge -pv' is called."""
		if len(self.mergequeue) == 0: return

		list = ""
		for k in self.mergequeue.keys():
			list += " '="+k+"'"
		
		s = ""
		print list
		if not force: s = "-pv "
		self._emerge(s+list, self.emergeIt)

	def unmerge (self, force = False):
		"""Unmerges everything in the umerge-queue. If force is 'False' (default) only "emerge -pv -C" is called."""
		if len(self.unmergequeue) == 0: return

		list = " ".join(self.unmergequeue)
		s = ""
		if not force: s = "-pv "
		self._emerge("-C "+s+list, self.unmergeIt)

	def removeAll (self, parentIt):
		"""Removes all children of a given parent TreeIter."""
		childIt = self.tree.iter_children(parentIt)

		while childIt:
			temp = childIt
			childIt = self.tree.iter_next(childIt)
			self.remove(temp)
	
	def remove (self, it):
		if self.tree.iter_parent(it): # NEVER remove our top stuff
			if self.tree.get_string_from_iter(it).split(":")[0] == self.tree.get_string_from_iter(self.emergeIt):
				del self.mergequeue[self.tree.get_value(it,0)]
			else:
				self.unmergequeue.remove(self.tree.get_value(it,0))
			
			self.tree.remove(it)

class PackageWindow:
	"""A window with data about a specfic package."""

	def cbChanged (self, combo, data = None):
		"""Callback for the changed ComboBox.
		It then rebuilds the useList and the checkboxes."""
		# remove old useList
		self.useListScroll.remove(self.useList)
		
		# build new
		self.useList = self.buildUseList()
		self.useListScroll.add(self.useList)
		self.updateCheckBoxes()

		self.useListScroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)

		# set emerge-button-label
		if not self.actualPackage().is_installed():
			self.emergeBtn.set_label("_Emerge")
		else:
			self.emergeBtn.set_label("_Unmerge")
		
		# refresh - make window as small as possible
		self.table.show_all()
		self.window.resize(1,1)
		return True

	def buildVersCombo (self):
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

		combo.connect("changed", self.cbChanged)
		
		return combo

	def actualPackage (self):
		"""Returns the actual package (a geneticone.Package-object)."""
		return self.packages[self.vCombo.get_active()]

	def cbButtonPressed (self, b, event, data = None):
		"""Callback for pressed checkboxes. Just quits the event-loop - no redrawing."""
		b.emit_stop_by_name("button-press-event")
		return True

	def cbEmergeClicked (self, button, data = None):
		"""Adds the package to the EmergeQueue."""
		if not geneticone.am_i_root():
			errorMB = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "You cannot (un)merge without being root.")
			errorMB.run()
			errorMB.destroy()
		else:
			unmerge = self.actualPackage().is_installed()
			self.queue.append(self.actualPackage().get_cpv(), unmerge)
			self.window.destroy()
		return True

	def updateCheckBoxes (self):
		"""Updates the checkboxes."""
		self.installedCheck.set_active(self.actualPackage().is_installed())
		self.maskedCheck.set_active(self.actualPackage().is_masked())
		self.testingCheck.set_active((self.actualPackage().get_mask_status() % 3) == 1)

	def buildUseList (self):
		"""Builds the useList."""
		store = gtk.ListStore(bool, str, str)

		pkg = self.actualPackage()
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

	def cbSizeCheck (self, event, data = None):
		if self.useListScroll:
			width, height = self.window.get_size()
			if height > gtk.gdk.screen_height():
				self.window.set_default_size(width, gtk.gdk.screen_height())
				self.window.resize(width, gtk.gdk.screen_height())
				self.useListScroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

		return False

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
		self.vCombo = self.buildVersCombo()
		self.table.attach(self.vCombo, 0, 1, 1, 2, yoptions = gtk.FILL)

		# the label (must be here, because it depends on the combo box)
		desc = self.actualPackage().get_env_var("DESCRIPTION")
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
		self.installedCheck.connect("button-press-event", self.cbButtonPressed)
		self.installedCheck.set_label("Installed")		
		checkHB.pack_start(self.installedCheck, True, False)

		self.maskedCheck = gtk.CheckButton()
		self.maskedCheck.connect("button-press-event", self.cbButtonPressed)
		self.maskedCheck.set_label("Masked")		
		checkHB.pack_start(self.maskedCheck, True, False)

		self.testingCheck = gtk.CheckButton()
		self.testingCheck.connect("button-press-event", self.cbButtonPressed)
		self.testingCheck.set_label("Testing")
		checkHB.pack_start(self.testingCheck, True, False)

		# use list
		self.useList = self.buildUseList()
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
		self.emergeBtn.connect("clicked", self.cbEmergeClicked)
		buttonHB.pack_start(self.emergeBtn)
		buttonHB.pack_start(self.cancelBtn)

		# current status
		self.cbChanged(self.vCombo)

		# show
		self.window.show_all()

class MainWindow:
	"""Application main window."""
	
	def cbDelete (self, widget, data = None):
		"""Returns false -> window is deleted."""
		return False

	def cbDestroy (self, widget, data = None):
		"""Calls main_quit()."""
		gtk.main_quit()

	def createMainMenu (self):
		"""Creates the main menu."""
		# the menu-list
		mainMenuDesc = [
				( "/_File", None, None, 0, "<Branch>"),
				( "/File/_Close", None, self.cbDestroy, 0, "")
				]
		self.itemFactory = gtk.ItemFactory(gtk.MenuBar, "<main>", None)
		self.itemFactory.create_items(mainMenuDesc)
		return self.itemFactory.get_widget("<main>")

	def cbCatListSelection (self, view, data = None):
		"""Callback for a category-list selection. Updates the package list with these packages in the category."""
		if view == self.catList: # be sure it is the catList
			# get the selected category
			sel = view.get_selection()
			store, it = sel.get_selected()
			
			if it:
				# remove old one
				self.scroll_2.remove(self.pkgList)
				
				# create new package list
				self.pkgList = self.createPkgList(store.get_value(it,0))
				self.scroll_2.add(self.pkgList)
				self.scroll_2.show_all()
		return False

	def cbRowActivated (self, view, path, col, store = None):
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

	def createCatList (self):
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
		view.connect("cursor-changed", self.cbCatListSelection)
		view.connect("row-activated", lambda v,p,c : self.cbCatListSelection(v))
		view.set_search_column(0)

		return view

	packages = {} # directory category -> [packages]
	def createPkgList (self, name = None):
		"""Creates the package list. Gets the name of the category."""
		self.selCatName = name # actual category
		
		store = gtk.ListStore(str)

		# calculate packages
		if name:
			if name not in self.packages: # only calc packages if not already done
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
		pkgList.connect("row-activated", self.cbRowActivated, store)

		return pkgList

	def cbRemoveClicked (self, button, data = None):
		selected = self.emergeView.get_selection()

		if selected:
			model, iter = selected.get_selected()

			if not model.iter_parent(iter): # top-level
				if model.iter_n_children(iter) > 0: # and has children which can be removed :)
					askMB = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you really want to clear the whole queue?")
					if askMB.run() == gtk.RESPONSE_YES :
						self.queue.removeAll(iter)
					askMB.destroy()
			elif model.iter_parent(model.iter_parent(iter)): # this is in the 3rd level => dependency
				infoMB = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "You cannot remove dependencies. :)")
				infoMB.run()
				infoMB.destroy()
			else:
				self.queue.remove(iter)
		
		return True

	def __init__ (self):
		"""Build up window"""

		# window
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_title("Genetic")
		self.window.connect("delete_event", self.cbDelete)
		self.window.connect("destroy", self.cbDestroy)
		self.window.set_border_width(2)
		self.window.set_geometry_hints (self.window, min_width = 600, min_height = 700, max_height = gtk.gdk.screen_height(), max_width = gtk.gdk.screen_width())
		self.window.set_resizable(True)

		# main vb
		vb = gtk.VBox(False, 1)
		self.window.add(vb)

		# menubar
		menubar = self.createMainMenu()
		vb.pack_start(menubar, False)
		
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
		self.catList = self.createCatList()
		self.scroll_1.add(self.catList)
		
		# create pkg list
		self.pkgList = self.createPkgList()
		self.scroll_2.add(self.pkgList)
		
		# queue list
		queueVB = gtk.VBox(False, 0)
		hb.pack_start(queueVB, True, True)
		
		emergeStore = gtk.TreeStore(str)
		self.emergeView = gtk.TreeView(emergeStore)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Queue", cell, text = 0)
		self.emergeView.append_column(col)
		self.emergeView.connect("row-activated", self.cbRowActivated, emergeStore)
		queueVB.pack_start(self.emergeView, True, True)

		# buttons right unter the queue list
		buttonBox = gtk.HButtonBox()
		queueVB.pack_start(buttonBox, False)
		emergeBtn = gtk.Button("_Emerge")
		emergeBtn.connect("clicked", lambda a: self.queue.emerge(force=True))
		unmergeBtn = gtk.Button("_Unmerge")
		unmergeBtn.connect("clicked", lambda a: self.queue.unmerge(force=True))
		removeBtn = gtk.Button("_Remove")
		removeBtn.connect("clicked", self.cbRemoveClicked)
		buttonBox.pack_start(emergeBtn)
		buttonBox.pack_start(removeBtn)
		buttonBox.pack_start(unmergeBtn)
		
		# the terminal
		term = vte.Terminal()
		term.set_scrollback_lines(1024)
		term.set_scroll_on_output(True)
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
		self.queue = EmergeQueue(console=term, tree = emergeStore)
	
	def main (self):
		"""Main."""
		gtk.main()

def blockedDialog (blocked, blocks):
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, blocked+" is blocked by "+blocks+".\nPlease unmerge the blocking package.")
	dialog.run()
	dialog.destroy()

if __name__ == "__main__":
	m = MainWindow()
	m.main()
