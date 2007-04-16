# -*- coding: utf-8 -*-
#
# File: portato/gui/qt/windows.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

# qt4
from PyQt4 import Qt, uic
import sip

# our backend stuff
from portato.helper import *
from portato.constants import CONFIG_LOCATION, VERSION, DATA_DIR
from portato.backend import flags, system
from portato.backend.exceptions import *

from portato.gui.gui_helper import Database, Config, EmergeQueue

# own GUI stuff
from terminal import QtConsole
from tree import QtTree
from dialogs import *
from helper import qCheck, qIsChecked

import types

UI_DIR = DATA_DIR+"ui/"

class WindowMeta (sip.wrappertype, type):

	def __new__ (cls, name, bases, dict):
		new_bases = uic.loadUiType(UI_DIR+name+".ui")
		dict.update(_bases = new_bases)
		dict.update(_qt_base = new_bases[1])
		return super(WindowMeta, cls).__new__(cls, name, new_bases+bases, dict)

	def __init__ (cls, name, bases, dict):
		b = dict["_bases"]
		del dict["_bases"]
		super(WindowMeta, cls).__init__(name, b+bases, dict)

class Window (object):

	def __init__(self, parent = None):
		self._qt_base.__init__(self, parent)
		self.setupUi(self)

	@staticmethod
	def watch_cursor (func):
		"""This is a decorator for functions being so time consuming, that it is appropriate to show the watch-cursor."""
		def wrapper (*args, **kwargs):
			ret = None

			Qt.QApplication.setOverrideCursor(Qt.Qt.WaitCursor)
			try:
				ret = func(*args, **kwargs)
			finally:
				Qt.QApplication.restoreOverrideCursor()

			return ret

		return wrapper

class AboutDialog (Window):
	"""A window showing the "about"-informations."""
	__metaclass__ = WindowMeta

	def __init__ (self, parent = None):
		Window.__init__(self, parent)

		self.label.setText("""
<font size=5><b>Portato v.%s</b></font><br><br>
A Portage-GUI<br>
<br>		
This software is licensed under the terms of the GPLv2.<br>
Copyright (C) 2006-2007 Ren&eacute; 'Necoro' Neumann &lt;necoro@necoro.net&gt;<br>
<br>
<font size=1>Thanks to Fred for support and ideas :P</font>""" % VERSION)

		self.adjustSize()

class SearchDialog (Window):
	"""A window showing the results of a search process."""
	__metaclass__ = WindowMeta

	def __init__ (self, parent, list, jumpTo):
		"""Constructor.

		@param parent: parent-window
		@type parent: Qt.QWidget
		@param list: list of results to show
		@type list: string[]
		@param jumpTo: function to call if "OK"-Button is hit
		@type jumpTo: function(string)"""

		Window.__init__(self, parent)

		self.comboBox.addItems(list)
		self.comboBox.setCurrentIndex(0)
		self.jumpTo = jumpTo

		Qt.QObject.connect(self, Qt.SIGNAL("accepted()"), self.finish)

	def finish (self):
		s = str(self.comboBox.currentText())
		self.done(0)
		self.jumpTo(s)

class PreferenceWindow (Window):
	"""Window displaying some preferences."""
	
	__metaclass__ = WindowMeta

	# all checkboxes in the window
	# widget name -> option name
	checkboxes = {
			"debugCheck"	: "debug_opt",
			"deepCheck"		: "deep_opt",
			"newUseCheck"	: "newuse_opt",
			"maskCheck"		: "maskPerVersion_opt",
			"useCheck"		: "usePerVersion_opt",
			"testingCheck"	: "testingPerVersion_opt"
			}
	
	# all edits in the window
	# widget name -> option name
	edits = {
			"maskEdit"		: "maskFile_opt",
			"testingEdit"	: "testingFile_opt",
			"useEdit"		: "useFile_opt",
			"syncCmdEdit"	: "syncCmd_opt"
			}

	def __init__ (self, parent, cfg):

		Window.__init__(self, parent)

		self.cfg = cfg
		
		palette = self.hintLabel.palette()
		palette.setColor(Qt.QPalette.Active, Qt.QPalette.Window, Qt.QColor(Qt.Qt.yellow))
		self.hintLabel.setPalette(palette)

		# the checkboxes
		for box in self.checkboxes:
			val = self.checkboxes[box]
			box = self.__getattribute__(box)
			if type(val) == types.TupleType:
				box.setCheckState(qCheck(self.cfg.get_boolean(val[0], section = self.cfg.const[val[1]])))
			else:
				box.setCheckState(qCheck(self.cfg.get_boolean(val)))

		# the edits
		for edit in self.edits:
			_edit = self.__getattribute__(edit)
			_edit.setText(self.cfg.get(self.edits[edit]))

		Qt.QObject.connect(self, Qt.SIGNAL("accepted()"), self.finish)

	def _save (self):
		"""Sets all options in the Config-instance."""
		
		for box in self.checkboxes:
			val = self.checkboxes[box]
			box = self.__getattribute__(box)
			if type(val) == types.TupleType:
				self.cfg.set_boolean(val[0], qIsChecked(box.checkState()), section = self.cfg.const[val[1]])
			else:
				self.cfg.set_boolean(val, qIsChecked(box.checkState()))

		for edit in self.edits:
			_edit = self.__getattribute__(edit)
			self.cfg.set(self.edits[edit], _edit.text())

	def finish (self):
		"""Saves and writes to config-file."""
		self._save()
		try:
			self.cfg.write()
		except IOError, e:
			io_ex_dialog(self, e)

class PackageDetails:

	def __init__ (self, window):
		self.window = window
		self.window.pkgTab.setHidden(True)
		self.window.tabWidget.removeTab(0)

		self.window.installedCheck.blockSignals(True)

		# combo
		Qt.QObject.connect(self.window.versCombo, Qt.SIGNAL("currentIndexChanged(int)"), self.cb_combo_changed)
		
		# buttons
		Qt.QObject.connect(self.window.pkgEmergeBtn, Qt.SIGNAL("clicked()"), self.cb_emerge_clicked)
		Qt.QObject.connect(self.window.pkgUnmergeBtn, Qt.SIGNAL("clicked()"), self.cb_unmerge_clicked)
		Qt.QObject.connect(self.window.pkgRevertBtn, Qt.SIGNAL("clicked()"), self.cb_revert_clicked)

		# checkboxes
		Qt.QObject.connect(self.window.maskedCheck, Qt.SIGNAL("clicked(bool)"), self.cb_masked_clicked)
		Qt.QObject.connect(self.window.testingCheck, Qt.SIGNAL("clicked(bool)"), self.cb_testing_clicked)

		# useflags
		Qt.QObject.connect(self.window.useList, Qt.SIGNAL("itemClicked(QTreeWidgetItem*, int)"), self.cb_use_flag_changed)

	def update (self, cp, queue = None, version = None, doEmerge = True, instantChange = None):
		"""Updates the table to show the contents for the package.
		
		@param cp: the selected package
		@type cp: string (cp)
		@param queue: emerge-queue (if None the emerge-buttons are disabled)
		@type queue: EmergeQueue
		@param version: if not None, specifies the version to select
		@type version: string
		@param doEmerge: if False, the emerge buttons are disabled
		@type doEmerge: False
		@param instantChange: if not None, the item given is updated immediatly
		@type instantChange: Qt.QTreeWidgetItem"""

		self.cp = cp
		self.version = version
		self.queue = queue
		self.doEmerge = doEmerge
		self.instantChange = instantChange
		
		# packages and installed packages
		self.packages = system.sort_package_list(system.find_packages(cp, masked = True))
		self.instPackages = system.sort_package_list(system.find_installed_packages(cp, masked = True))

		# comboBox
		self.set_combo()

		# the labels
		desc = self.actual_package().get_package_settings("DESCRIPTION").replace("&","&amp;")
		
		if not desc: 
			desc = "<no description>"
		else:
			desc = "<b>%s</b>" % desc
		
		self.window.descLabel.setText(desc)
		self.window.nameLabel.setText("<i><u>%s</i></u>" % self.actual_package().get_cp())

		# disable buttons when emerging is not allowed
		if not self.queue or not self.doEmerge: 
			self.window.pkgEmergeBtn.setEnabled(False)
			self.window.pkgUnmergeBtn.setEnabled(False)
		
		# first update -> show
		if self.window.pkgTab.isHidden():
			self.window.tabWidget.insertTab(0, self.window.pkgTab, "Package")
			self.window.pkgTab.setHidden(False)

		self.window.tabWidget.setCurrentIndex(self.window.PKG_PAGE)

	def set_combo (self):
		self.window.versCombo.clear()
		self.window.versCombo.addItems([x.get_version() for x in self.packages])

		try:
			best_version = ""
			if self.version:
				best_version = self.version
			else:
				best_version = system.find_best_match(self.packages[0].get_cp(), (self.instPackages != [])).get_version()
			
			for i in range(len(self.packages)):
				if self.packages[i].get_version() == best_version:
					self.window.versCombo.setCurrentIndex(i)
		except AttributeError:
			self.window.versCombo.setCurrentIndex(0)

	def build_use_list (self):
		self.window.useList.clear()
		self.window.useList.setHeaderLabels(["Enabled","Flag","Description"])
		
		pkg = self.actual_package()
		pkg_flags = pkg.get_all_use_flags()
		pkg_flags.sort()
		
		actual_exp = None
		actual_exp_it = self.window.useList
		
		for use in pkg_flags:
			exp = pkg.use_expanded(use, suggest = actual_exp)
			if exp is not None:
				if exp != actual_exp:
					actual_exp_it = Qt.QTreeWidgetItem(self.window.useList, ["", exp, ""])
					actual_exp = exp
			else:
				actual_exp_it = self.window.useList
				actual_exp = None

			item = Qt.QTreeWidgetItem(actual_exp_it, ["", use, system.get_use_desc(use, self.cp)])
			item.setCheckState(0, qCheck(pkg.is_use_flag_enabled(use)))

	def _update_keywords (self, emerge, update = False):
		if emerge:
			try:
				try:
					self.queue.append(self.actual_package().get_cpv(), unmerge = False, update = update)
				except PackageNotFoundException, e:
					if unmask_dialog(self.window, e[0]) == Qt.QMessageBox.Yes :
						self.queue.append(self.actual_package().get_cpv(), unmerge = False, unmask = True, update = update)
			except BlockedException, e:
				blocked_dialog(self.window, e[0], e[1])
		else:
			try:
				self.queue.append(self.actual_package().get_cpv(), unmerge = True)
			except PackageNotFoundException, e:
				debug("Package could not be found",e[0], error = 1)


	def actual_package (self):
		"""Returns the actual selected package.
		
		@returns: the actual selected package
		@rtype: backend.Package"""
		
		return self.packages[self.window.versCombo.currentIndex()]

	def cb_emerge_clicked (self):
		"""Callback for pressed emerge-button. Adds the package to the EmergeQueue."""
		if not am_i_root():
			not_root_dialog(self.window)
		else:
			self._update_keywords(True)
			self.window.tabWidget.setCurrentIndex(self.window.QUEUE_PAGE)
		return True

	def cb_unmerge_clicked (self):
		"""Callback for pressed unmerge-button. Adds the package to the EmergeQueue."""
		if not am_i_root():
			not_root_dialog(self.window)
		else:
			self._update_keywords(False)
			self.window.tabWidget.setCurrentIndex(self.window.QUEUE_PAGE)
		return True

	def cb_revert_clicked (self, button):
		"""Callback for pressed revert-button."""
		self.actual_package().remove_new_use_flags()
		self.actual_package().remove_new_masked()
		self.actual_package().remove_new_testing()
		self.cb_combo_changed()
		if self.instantChange:
			self._update_keywords(True, update = True)
		return True
	
	def cb_testing_clicked (self, status):
		"""Callback for toggled testing-checkbox."""
		button = self.window.testingCheck

		if self.actual_package().is_testing(use_keywords = False) == status:
			return

		if not self.actual_package().is_testing(use_keywords = True):
			self.actual_package().set_testing(False)
			button.setText("Testing")
			button.setCheckState(qCheck(True))
		else:
			self.actual_package().set_testing(True)
			if self.actual_package().is_testing(use_keywords=False):
				button.setText("(Testing)")
				button.setCheckState(qCheck(True))

		if self.instantChange:
			self._update_keywords(True, update = True)
		
	def cb_masked_clicked (self, status):
		"""Callback for toggled masking-checkbox."""
		pkg = self.actual_package()
		button = self.window.maskedCheck

		if pkg.is_masked(use_changed = False) == status and not pkg.is_locally_masked():
			return

		if pkg.is_locally_masked() and status:
			return False
	
		if not pkg.is_masked(use_changed = True):
			pkg.set_masked(True)
			if pkg.is_locally_masked():
				button.setText("Masked by User")
			else:
				button.setText("Masked")

			button.setCheckState(qCheck(True))
		
		else:
			locally = pkg.is_locally_masked()
			pkg.set_masked(False)

			if pkg.is_masked(use_changed=False) and not locally:
				button.setText("(Masked)")
				button.setCheckState(qCheck(True))
			else:
				button.setText("Masked")
		
		if self.instantChange:
			self._update_keywords(True, update = True)
		
		return True
	
	def cb_use_flag_changed (self, item, col):
		if col != 0: return
		
		flag = str(item.text(1))
		pkg = self.actual_package()
		
		if flag in pkg.get_global_settings("USE_EXPAND").split(" "): # ignore expanded flags
			return

		checked = qIsChecked(item.checkState(0))

		prefix = ""
		if not checked: prefix = "-"
		
		pkg.set_use_flag(prefix+flag)	
		if self.instantChange:
			self._update_keywords(True, update = True)
			self.window.queueTree.make_tooltip(self.instantChange)

	def cb_combo_changed (self):
		"""Callback for the changed ComboBox.
		It then rebuilds the useList and the checkboxes."""
		
		# build new
		self.build_use_list()
		pkg = self.actual_package()

		shown = Qt.QSizePolicy(Qt.QSizePolicy.MinimumExpanding, Qt.QSizePolicy.Fixed)
		hidden = Qt.QSizePolicy(Qt.QSizePolicy.Ignored, Qt.QSizePolicy.Fixed)
		
		#
		# rebuild the buttons and checkboxes in all the different manners which are possible
		#
		if (not pkg.is_in_system()) or pkg.is_missing_keyword():
			if not pkg.is_in_system():
				self.window.missingLabel.setSizePolicy(hidden)
				self.window.notInSysLabel.setSizePolicy(shown)
			else: # missing keyword
				self.window.missingLabel.setSizePolicy(shown)
				self.window.notInSysLabel.setSizePolicy(hidden)
			
			self.window.installedCheck.setSizePolicy(hidden)
			self.window.maskedCheck.setSizePolicy(hidden)
			self.window.testingCheck.setSizePolicy(hidden)
			self.window.pkgEmergeBtn.setEnabled(False)
		else: # normal package
			self.window.missingLabel.setSizePolicy(hidden)
			self.window.notInSysLabel.setSizePolicy(hidden)
			self.window.installedCheck.setSizePolicy(shown)
			self.window.maskedCheck.setSizePolicy(shown)
			self.window.testingCheck.setSizePolicy(shown)
			if self.doEmerge:
				self.window.pkgEmergeBtn.setEnabled(True)
			self.window.installedCheck.setCheckState(qCheck(pkg.is_installed()))
			
			if pkg.is_masked(use_changed = False) and not pkg.is_masked(use_changed = True):
				self.window.maskedCheck.setText("(Masked)")
			else:
				self.window.maskedCheck.setText("Masked")
			
			if pkg.is_locally_masked():
				self.window.maskedCheck.setText("Masked by User")
				self.window.maskedCheck.setCheckState(qCheck(True))
			else:
				self.window.maskedCheck.setCheckState(qCheck(pkg.is_masked(use_changed = False)))
			
			if pkg.is_testing(use_keywords = False) and not pkg.is_testing(use_keywords = True):
				self.window.testingCheck.setText("(Testing)")
			else:
				self.window.testingCheck.setText("Testing")
			
			self.window.testingCheck.setCheckState(qCheck(pkg.is_testing(use_keywords = False)))

		if self.doEmerge:
			# set emerge-button-label
			if not self.actual_package().is_installed():
				self.window.pkgEmergeBtn.setText("E&merge")
				self.window.pkgUnmergeBtn.setEnabled(False)
			else:
				self.window.pkgEmergeBtn.setText("Re&merge")
				self.window.pkgUnmergeBtn.setEnabled(True)
		
class MainWindow (Window):

	__metaclass__ = WindowMeta

	# NOTEBOOK PAGE CONSTANTS
	PKG_PAGE = 0
	QUEUE_PAGE = 1
	CONSOLE_PAGE = 2
	
	def __init__ (self):
		Window.__init__(self)

		self.setWindowTitle(("Portato (%s)" % VERSION))
		self.statusbar.showMessage("Portato - A Portage GUI")

		self.doUpdate = False
		self.pkgDetails = PackageDetails(self)
		
		# package db
		self.db = Database()
		self.db.populate()

		# config
		try:
			self.cfg = Config(CONFIG_LOCATION)
		except IOError, e:
			io_ex_dialog(self, e)
			raise

		self.cfg.modify_external_configs()

		# the two lists
		self.build_pkg_list()
		self.build_cat_list()
		Qt.QObject.connect(self.selCatListModel, Qt.SIGNAL("currentChanged(QModelIndex, QModelIndex)"), self.cb_cat_list_selected)
		Qt.QObject.connect(self.selPkgListModel, Qt.SIGNAL("currentChanged(QModelIndex, QModelIndex)"), self.cb_pkg_list_selected)

		# build console
		self.console = QtConsole(self.consoleTab)
		self.consoleLayout = Qt.QVBoxLayout()
		self.consoleLayout.setMargin(0)
		self.consoleLayout.setSpacing(0)
		self.consoleTab.setLayout(self.consoleLayout)
		self.consoleLayout.addWidget(self.console)
		Qt.QObject.connect(self, Qt.SIGNAL("doTitleUpdate"), self._title_update)

		# build queueList
		self.queueList.setHeaderLabels(["Package", "Additional infos"])
		self.queueTree = QtTree(self.queueList)
		Qt.QObject.connect(self.queueList.model(), Qt.SIGNAL("rowsInserted (const QModelIndex&, int, int)"), self.cb_queue_list_items_added)
		Qt.QObject.connect(self.queueList, Qt.SIGNAL("expanded (const QModelIndex&)"), self.cb_queue_list_items_added)
		Qt.QObject.connect(self.queueList, Qt.SIGNAL("itemActivated (QTreeWidgetItem*, int)"), self.cb_queue_list_item_selected)
		Qt.QObject.connect(self.queueList, Qt.SIGNAL("itemDoubleClicked (QTreeWidgetItem*, int)"), self.cb_queue_list_item_selected)

		# set emerge queue
		self.queue = EmergeQueue(console = self.console, tree = self.queueTree, db = self.db, title_update = self.title_update)

		self.show()
	
	def title_update (self, title):
		self.emit(Qt.SIGNAL("doTitleUpdate"), title)

	def _title_update (self, title):
		if title == None: title = "Console"
		else: title = ("Console (%s)" % title)

		self.tabWidget.setTabText(self.CONSOLE_PAGE, title)

	def jump_to (self, cp):
		"""Is called when we want to jump to a specific package."""
		self.pkgDetails.update(cp, self.queue)

	def fill_pkg_list (self, cat):
		self.pkgListModel.setStringList([name for (name,inst) in self.db.get_cat(cat)])

	def build_pkg_list (self):
		self.pkgListModel = Qt.QStringListModel([])
		self.pkgListModel.sort(0)
		self.selPkgListModel = Qt.QItemSelectionModel(self.pkgListModel)
		self.pkgList.setModel(self.pkgListModel)
		self.pkgList.setSelectionModel(self.selPkgListModel)

	def build_cat_list (self):
		self.catListModel = Qt.QStringListModel(system.list_categories())
		self.catListModel.sort(0)
		self.selCatListModel = Qt.QItemSelectionModel(self.catListModel)
		self.catList.setModel(self.catListModel)
		self.catList.setSelectionModel(self.selCatListModel)

	@Qt.pyqtSignature("")
	def on_aboutAction_triggered (self):
		AboutDialog(self).exec_()

	@Qt.pyqtSignature("")
	def on_prefAction_triggered (self):
		PreferenceWindow(self, self.cfg).exec_()
	
	@Qt.pyqtSignature("")
	@Window.watch_cursor
	def on_searchBtn_clicked (self):
		"""Do a search."""
		text = str(self.searchEdit.text())
		if text != "":
			packages = system.find_all_packages(text, withVersion = False)

			if packages == []:
				nothing_found_dialog(self)
			else:
				if len(packages) == 1:
					self.jump_to(packages[0])
				else:
					SearchDialog(self, packages, self.jump_to).exec_()

	@Qt.pyqtSignature("")
	def on_removeBtn_clicked (self):
		"""Removes a selected item in the (un)emerge-queue if possible."""
		selected = self.queueList.currentItem()

		if selected:
			if not selected.parent(): # top-level
				if self.queueTree.iter_has_children(selected): # and has children which can be removed :)
					if remove_queue_dialog(self) == Qt.QMessageBox.Yes :
						self.queue.remove_children(selected)
						self.doUpdate = False
			
			elif selected.parent().parent(): # this is in the 3rd level => dependency
				remove_deps_dialog(self)
			else:
				self.queue.remove_with_children(selected)
				self.doUpdate = False

	@Qt.pyqtSignature("")
	def on_emergeBtn_clicked (self):
		"""Do emerge."""
		
		self.tabWidget.setCurrentIndex(self.CONSOLE_PAGE)
		
		if len(flags.newUseFlags) > 0:
			changed_flags_dialog(self, "use flags")
			flags.write_use_flags()
		
		if len(flags.new_masked)>0 or len(flags.new_unmasked)>0 or len(flags.newTesting)>0:
			debug("new masked:",flags.new_masked)
			debug("new unmasked:", flags.new_unmasked)
			debug("new testing:", flags.newTesting)
			changed_flags_dialog(self, "masking keywords")
			flags.write_masked()
			flags.write_testing()
			system.reload_settings()
		
		if not self.doUpdate:
			self.queue.emerge(force=True, options = ["--nospinner"])
		else:
			self.queue.update_world(force=True, newuse = self.cfg.get_boolean("newuse_opt"), deep = self.cfg.get_boolean("deep_opt"), options = ["--nospinner"])
			self.doUpdate = False

	@Qt.pyqtSignature("")
	def on_unmergeBtn_clicked (self):
		"""Do unmerge."""

		self.tabWidget.setCurrentIndex(self.CONSOLE_PAGE)
		self.queue.unmerge(force = True)

	@Qt.pyqtSignature("")
	@Window.watch_cursor
	def on_updateBtn_clicked (self):
		if not am_i_root():
			not_root_dialog(self)
	
		else:
			updating = system.update_world(newuse = self.cfg.get_boolean("newuse_opt"), deep = self.cfg.get_boolean("deep_opt"))

			debug("updating list:", [(x.get_cpv(), y.get_cpv()) for x,y in updating],"--> length:",len(updating))
			try:
				try:
					for pkg, old_pkg in updating:
						self.queue.append(pkg.get_cpv(), unmask = False)
				except PackageNotFoundException, e:
					if unmask_dialog(self, e[0]) == Qt.QMessageBox.Yes:
						for pkg, old_pkg in updating:
							self.queue.append(pkg.get_cpv(), unmask = True)
			
			except BlockedException, e:
				blocked_dialog(self, e[0], e[1])
				self.queue.remove_children(self.queue.emergeIt)

			if len(updating): self.doUpdate = True

	def cb_queue_list_item_selected (self, item, col):
		if col == -1: return # nothing selected
		
		if self.queueTree.iter_has_parent(item):
			package = self.queueTree.get_value(item, self.queueTree.get_cpv_column())
			cat, name, vers, rev = system.split_cpv(package)
			if rev != "r0": vers = vers+"-"+rev
			self.pkgDetails.update(cat+"/"+name, queue = self.queue, version = vers, instantChange = item, doEmerge = False)

	def cb_queue_list_items_added (self, *args):
		self.queueList.resizeColumnToContents(0)

	def cb_cat_list_selected (self, index, prev):
		self.selCatName = str(index.data().toString())
		self.fill_pkg_list(self.selCatName)

	def cb_pkg_list_selected (self, index, prev):
		self.pkgDetails.update(self.selCatName+"/"+str(index.data().toString()), self.queue)
