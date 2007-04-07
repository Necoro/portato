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
from PyQt4 import QtGui, uic, QtCore
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

UI_DIR = DATA_DIR+"ui/"

#XXX: global variables are bad
app = QtGui.QApplication([])

def qCheck (check):
	if check:
		return QtCore.Qt.Checked
	else:
		return QtCore.Qt.Unchecked

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

class Window:

	def __init__(self, parent = None):
		self._qt_base.__init__(self, parent)
		self.setupUi(self)

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
		@type parent: QtGui.QWidget
		@param list: list of results to show
		@type list: string[]
		@param jump_to: function to call if "OK"-Button is hit
		@type jump_to: function(string)"""

		Window.__init__(self, parent)

		self.comboBox.addItems(list)
		self.comboBox.setCurrentIndex(0)
		self.jumpTo = jumpTo

		QtCore.QObject.connect(self, QtCore.SIGNAL("accepted()"), self.finish)

	def finish (self):
		s = str(self.comboBox.currentText())
		self.done(0)
		self.jumpTo(s)

class PackageDetails:

	def __init__ (self, window):
		self.window = window
		self.window.pkgTab.setHidden(True)
		self.window.tabWidget.removeTab(0)

		QtCore.QObject.connect(self.window.versCombo, QtCore.SIGNAL("currentIndexChanged(int)"), self.cb_combo_changed)
		QtCore.QObject.connect(self.window.pkgEmergeBtn, QtCore.SIGNAL("clicked()"), self.cb_emerge_clicked)

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
					actual_exp_it = QtGui.QTreeWidgetItem(self.window.useList, ["", exp, ""])
					actual_exp = exp
			else:
				actual_exp_it = self.window.useList
				actual_exp = None

			item = QtGui.QTreeWidgetItem(actual_exp_it, ["", use, system.get_use_desc(use, self.cp)])
			item.setCheckState(0, qCheck(pkg.is_use_flag_enabled(use)))

	def _update_keywords (self, emerge, update = False):
		if emerge:
			try:
				try:
					self.queue.append(self.actual_package().get_cpv(), unmerge = False, update = update)
				except PackageNotFoundException, e:
					if unmask_dialog(self.window, e[0]) == QtGui.QMessageBox.Yes :
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

	def cb_combo_changed (self, combo):
		"""Callback for the changed ComboBox.
		It then rebuilds the useList and the checkboxes."""
		
		# build new
		self.build_use_list()
		pkg = self.actual_package()

		shown = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
		hidden = QtGui.QSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Fixed)
		
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
		QtCore.QObject.connect(self.selCatListModel, QtCore.SIGNAL("currentChanged(QModelIndex, QModelIndex)"), self.cb_cat_list_selected)
		QtCore.QObject.connect(self.selPkgListModel, QtCore.SIGNAL("currentChanged(QModelIndex, QModelIndex)"), self.cb_pkg_list_selected)

		# build console
		self.console = QtConsole(self.consoleTab)
		self.consoleLayout = QtGui.QVBoxLayout()
		self.consoleLayout.setMargin(0)
		self.consoleLayout.setSpacing(0)
		self.consoleTab.setLayout(self.consoleLayout)
		self.consoleLayout.addWidget(self.console)

		# build queueList
		self.queueList.setHeaderLabels(["Package", "Additional infos"])
		self.queueTree = QtTree(self.queueList)

		QtCore.QObject.connect(self, QtCore.SIGNAL("doTitleUpdate"), self._title_update)

		# set emerge queue
		self.queue = EmergeQueue(console = self.console, tree = self.queueTree, db = self.db, title_update = self.title_update)

		self.show()
	
	def title_update (self, title):
		self.emit(QtCore.SIGNAL("doTitleUpdate"), title)

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
		self.pkgListModel = QtGui.QStringListModel([])
		self.pkgListModel.sort(0)
		self.selPkgListModel = QtGui.QItemSelectionModel(self.pkgListModel)
		self.pkgList.setModel(self.pkgListModel)
		self.pkgList.setSelectionModel(self.selPkgListModel)

	def build_cat_list (self):
		self.catListModel = QtGui.QStringListModel(system.list_categories())
		self.catListModel.sort(0)
		self.selCatListModel = QtGui.QItemSelectionModel(self.catListModel)
		self.catList.setModel(self.catListModel)
		self.catList.setSelectionModel(self.selCatListModel)

	@QtCore.pyqtSignature("")
	def on_aboutAction_triggered (self):
		AboutDialog(self).exec_()

	@QtCore.pyqtSignature("")
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

	@QtCore.pyqtSignature("")
	def on_removeBtn_clicked (self):
		"""Removes a selected item in the (un)emerge-queue if possible."""
		selected = self.queueList.currentItem()

		if selected:
			if not selected.parent(): # top-level
				if self.queueTree.iter_has_children(selected): # and has children which can be removed :)
					if remove_queue_dialog(self) == QtGui.QMessageBox.Yes :
						self.queue.remove_children(selected)
						self.doUpdate = False
			
			elif selected.parent().parent(): # this is in the 3rd level => dependency
				remove_deps_dialog(self)
			else:
				self.queue.remove_with_children(selected)
				self.doUpdate = False

	def cb_cat_list_selected (self, index, prev):
		self.selCatName = str(index.data().toString())
		self.fill_pkg_list(self.selCatName)

	def cb_pkg_list_selected (self, index, prev):
		self.pkgDetails.update(self.selCatName+"/"+str(index.data().toString()), self.queue)

	def main (self):
		app.exec_()

