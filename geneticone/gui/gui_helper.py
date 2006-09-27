#
# File: geneticone/gui/gui_helper.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 Necoro d.M.
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by Necoro d.M. <necoro@necoro.net>

import geneticone
from geneticone import flags

from subprocess import *
from threading import Thread

import pty
import vte

class EmergeQueue:
	"""This class manages the emerge queue."""
	
	def __init__ (self, tree = None, console = None, packages = None):
		"""Constructor.
		
		@param tree: Tree to append all the items to. Default: None.
		@type tree: gtk.TreeStore
		@param console: Output is shown here. Default: None
		@type console: vte.Terminal
		@param packages: The list of packages sorted by categories. We will delete the appropriate category if we updated sth. Default: None
		@type packages: dictionary: {category: list_of_packages}."""
		
		self.mergequeue = []
		self.unmergequeue = []
		self.iters = {}
		self.deps = {}
		self.tree = tree
		self.console = console
		self.packages = packages

		if self.tree: 
			self.emergeIt = self.tree.append(None, ["Emerge"])
			self.unmergeIt = self.tree.append(None, ["Unmerge"])
		else:
			self.emergeIt = self.unmergeIt = None

	def update_tree (self, it, cpv):
		"""This updates the tree recursivly. 

		@param it: iterator where to append
		@type it: gtk.TreeIter
		@param cpv: The package to append.
		@type cpv: string (cat/pkg-ver)
		
		@raise geneticone.BlockedException: When occured during dependency-calculation."""
		
		# get depencies
		if cpv in self.deps:
			return # in list already
		else:
			deps = geneticone.find_packages("="+cpv)[0].get_dep_packages()
			self.deps.update({cpv : deps})
		
		subIt = self.tree.append(it, [cpv])
		
		# recursive call
		for d in deps:
			try:
				self.update_tree(subIt, d)
			except geneticone.BlockedException, e:
				# remove the project
				while self.tree.iter_parent(subIt):
					subIt = self.tree.iter_parent(subIt)
				self.remove_children(subIt)
				raise e
		
		# add iter
		self.iters.update({cpv: subIt})

	def append (self, cpv, unmerge = False, update = False):
		"""Appends a cpv either to the merge queue or to the unmerge-queue.
		Also updates the tree-view.
		
		@param cpv: Package to add
		@type cpv: string (cat/pkg-ver)
		@param unmerge: Set to True if you want to unmerge this package - else False. Default: False
		@type unmerge: boolean
		@param update: Set to True if a package is going to be updated (e.g. if the use-flags changed). Default: False
		@type update: boolean"""
		
		if not unmerge:
			try:
				# insert dependencies
				pkg = geneticone.find_packages("="+cpv)[0]
				deps = pkg.get_dep_packages()
				
				if update:
					if deps == self.deps[cpv]:
						return # nothing changed - return
					else:
						parentIt = self.tree.iter_parent(self.iters[cpv])
						self.remove_children(self.iters[cpv], False) # this is needed to def delete everything
						self.remove(self.iters[cpv], False)
						self.update_tree(parentIt, cpv)
				else: # not update
					self.mergequeue.append(cpv)
					if self.emergeIt: self.update_tree(self.emergeIt, cpv)
			
			except geneticone.BlockedException, e : # there is sth blocked --> call blocked_dialog
				blocks = e[0]
				blocked_dialog(cpv, blocks)
				return
		else: # unmerge
			self.unmergequeue.append(cpv)
			if self.unmergeIt: # update tree
				self.tree.append(self.unmergeIt, [cpv])
	
	def _update_packages(self, packages, process = None):
		"""This updates the packages-list. It simply removes all affected categories so they have to be rebuilt.
		
		@param packages: The packages which we emerged.
		@type packages: list of cpvs
		@param process: The process we have to wait for before we can do our work. Default: None.
		@type process: subprocess.Popen"""

		if process: process.wait()
		for p in packages:
			try:
				cat = geneticone.split_package_name(p)[0] # get category
				while cat[0] in ["=",">","<","!"]:
					cat = cat[1:]
				print "Category: "+cat ,
				del self.packages[cat]
				print "marked for refreshing"
			except KeyError: # not in self.packages - ignore
				pass

	def _emerge (self, options, packages, it):
		"""Calls emerge and updates the terminal.
		
		@param options: options to send to emerge
		@type options: list
		@param packages: packages to emerge
		@type packages: list
		@param it: Iterator which points to an entry whose children will be removed after completion.
		@type it: gtk.TreeIter"""

		# open tty
		(master, slave) = pty.openpty()
		self.console.set_pty(master)
		
		# start emerge
		process = Popen(["/usr/bin/python","/usr/bin/emerge"]+options+packages, stdout = slave, stderr = STDOUT, shell = False)
		Thread(target=self._update_packages, args=(packages, process)).start()
		
		# remove
		self.remove_children(it)

	def emerge (self, force = False):
		"""Emerges everything in the merge-queue.
		
		@param force: If False, '-pv' is send to emerge. Default: False.
		@type force: boolean"""

		if len(self.mergequeue) == 0: return # nothing in queue
		
		# prepare package-list
		list = []
		for k in self.mergequeue:
			list += ["="+k]
		
		s = []
		if not force: s = ["-pv"]
		
		self._emerge(s, list, self.emergeIt)

	def unmerge (self, force = False):
		"""Unmerges everything in the umerge-queue.

		@param force: If False, '-pv' is send to emerge. Default: False.
		@type force: boolean"""
		
		if len(self.unmergequeue) == 0: return # nothing in queue

		list = self.unmergequeue[:] # copy the unmerge-queue
		
		# set options
		s = ["-C"]
		if not force: s = ["-Cpv"]
		
		self._emerge(s,list, self.unmergeIt)

	def remove_children (self, parentIt, removeNewFlags = True):
		"""Removes all children of a given parent TreeIter recursivly.
		
		@param parentIt: The iter from which to remove all children.
		@type parentIt: gtk.TreeIter
		@param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
		@type removeNewFlags: boolean"""

		childIt = self.tree.iter_children(parentIt)

		while childIt:
			if (self.tree.iter_has_child(childIt)): # recursive call
				self.remove_children(childIt, removeNewFlags)
			temp = childIt
			childIt = self.tree.iter_next(childIt)
			self.remove(temp, removeNewFlags)

	def remove (self, it, removeNewFlags = True):
		"""Removes a specific item in the tree. This does not remove the top-entries.
		
		@param it: Iterator which points to the entry we are going to remove.
		@type it: gtk.TreeIter
		@param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
		@type removeNewFlags: boolean"""
		
		if self.tree.iter_parent(it): # NEVER remove our top stuff
			cpv = self.tree.get_value(it,0)
			if self.tree.get_string_from_iter(it).split(":")[0] == self.tree.get_string_from_iter(self.emergeIt): # in Emerge
				del self.iters[cpv]
				del self.deps[cpv]
				try:
					self.mergequeue.remove(cpv)
				except ValueError: # this is a dependency - ignore
					pass
				if removeNewFlags: flags.remove_new_use_flags(cpv)
			
			else: # in Unmerge
				self.unmergequeue.remove(cpv)
			
			self.tree.remove(it)

def blocked_dialog (blocked, blocks):
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, blocked+" is blocked by "+blocks+".\nPlease unmerge the blocking package.")
	dialog.run()
	dialog.destroy()
