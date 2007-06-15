# -*- coding: utf-8 -*-
#
# File: portato/gui/gui_helper.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

# some backend things
from portato import backend
from portato.backend import flags, system, set_system
from portato.helper import *
from portato import plugin

# parser
from portato.config_parser import ConfigParser

# the wrapper
from wrapper import Console, Tree

# some stuff needed
from subprocess import Popen, PIPE, STDOUT
from threading import Thread
import pty
import time
import os
import signal

class Config: # XXX: This needs to be replaced - the const-dict is just messy
	"""Wrapper around a ConfigParser and for additional local configurations."""
	const = {
			"main_sec" : "Main",
			"gtk_sec" : "Gtk",
			"qt_sec" : "Qt",
			"gui_sec" : "Gui",
			"usePerVersion_opt" : "usePerVersion",
			"useFile_opt" : "usefile",
			"maskFile_opt" : "maskfile",
			"maskPerVersion_opt" : "maskPerVersion",
			"testingFile_opt" : "keywordfile",
			"testingPerVersion_opt" : "keywordperversion",
			"debug_opt" : "debug",
			"oneshot_opt" : "oneshot",
			"deep_opt" : "deep",
			"newuse_opt" : "newuse",
			"syncCmd_opt" : "synccommand",
			"useTips_opt" : "showusetips",
			"consolefont_opt" : "consolefont",
			"pkgIcons_opt" : "packageIcons",
			"system_opt" : "system",
			"systray_opt" : "showsystray",
			"minimize_opt" : "hideonminimize",
			"updateTitle_opt" : "updatetitle"
			}
	
	def __init__ (self, cfgFile):
		"""Constructor.

		@param cfgFile: path to config file
		@type cfgFile: string"""

		# init ConfigParser
		self._cfg = ConfigParser(cfgFile)
		
		# read config
		self._cfg.parse()

		# local configs
		self.local = {}

	def get(self, name, section=const["main_sec"], constName = True):
		"""Gets an option.
		
		@param name: name of the option
		@type name: string
		@param section: section to look in; default is Main-Section
		@type section: string
		@param constName: If True (the default), the option names are first looked up in the const-dict.
		@type constName: boolean
		@return: the option's value
		@rtype: string"""

		if constName:
			name = self.const[name]

		return self._cfg.get(name, section)

	def get_boolean(self, name, section=const["main_sec"], constName = True):
		"""Gets a boolean option.
			
		@param name: name of the option
		@type name: string
		@param section: section to look in; default is Main-Section
		@type section: string
		@param constName: If True (the default), the option names are first looked up in the const-dict.
		@type constName: boolean
		@return: the option's value
		@rtype: boolean"""

		if constName:
			name = self.const[name]

		return self._cfg.get_boolean(name, section)

	def modify_flags_config (self):
		"""Sets the internal config of the L{flags}-module.
		@see: L{flags.set_config()}"""

		flagCfg = {
				"usefile": self.get("useFile_opt"), 
				"usePerVersion" : self.get_boolean("usePerVersion_opt"),
				"maskfile" : self.get("maskFile_opt"),
				"maskPerVersion" : self.get_boolean("maskPerVersion_opt"),
				"testingfile" : self.get("testingFile_opt"),
				"testingPerVersion" : self.get_boolean("testingPerVersion_opt")}
		flags.set_config(flagCfg)

	def modify_debug_config (self):
		"""Sets the external debug-config.
		@see: L{helper.set_debug()}"""
		set_debug(self.get_boolean("debug_opt"))

	def modify_system_config (self):
		"""Sets the system config.
		@see: L{backend.set_system()}"""
		set_system(self.get("system_opt"))
	
	def modify_external_configs (self):
		"""Convenience function setting all external configs."""
		self.modify_debug_config()
		self.modify_flags_config()
		self.modify_system_config()

	def set_local(self, cpv, name, val):
		"""Sets some local config.

		@param cpv: the cpv describing the package for which to set this option
		@type cpv: string (cpv)
		@param name: the option's name
		@type name: string
		@param val: the value to set
		@type val: any"""
		
		if not cpv in self.local:
			self.local[cpv] = {}

		self.local[cpv].update({name:val})

	def get_local(self, cpv, name):
		"""Returns something out of the local config.

		@param cpv: the cpv describing the package from which to get this option
		@type cpv: string (cpv)
		@param name: the option's name
		@type name: string
		@return: value stored for the cpv and name or None if not found
		@rtype: any"""

		if not cpv in self.local:
			return None
		if not name in self.local[cpv]:
			return None

		return self.local[cpv][name]

	def set(self, name, val, section=const["main_sec"], constName = True):
		"""Sets an option.
		
		@param name: name of the option
		@type name: string
		@param val: value to set the option to
		@type val: string
		@param section: section to look in; default is Main-Section
		@type section: string
		@param constName: If True (the default), the option names are first looked up in the const-dict.
		@type constName: boolean"""

		if constName:
			name = self.const[name]

		self._cfg.set(name, val, section)

	def set_boolean (self, name, val, section=const["main_sec"], constName = True):
		"""Sets a boolean option.
		
		@param name: name of the option
		@type name: string
		@param val: value to set the option to
		@type val: boolean
		@param section: section to look in; default is Main-Section
		@type section: string
		@param constName: If True (the default), the option names are first looked up in the const-dict.
		@type constName: boolean"""

		if constName:
			name = self.const[name]

		self._cfg.set_boolean(name, val, section)

	def write(self):
		"""Writes to the config file and modify any external configs."""
		self._cfg.write()
		self.modify_external_configs()

class Database:
	"""An internal database which holds a simple dictionary cat -> [package_list]."""

	def __init__ (self):
		"""Constructor."""
		self._db = {}

	def populate (self, category = None):
		"""Populates the database.
		
		@param category: An optional category - so only packages of this category are inserted.
		@type category: string"""
		
		# get the lists
		packages = system.find_all_packages(name = category, withVersion = False)
		installed = system.find_all_installed_packages(name = category, withVersion = False)
		
		# cycle through packages
		for p in packages:
			list = p.split("/")
			cat = list[0]
			pkg = list[1]
			if not cat in self._db: self._db[cat] = []
			self._db[cat].append((pkg, p in installed))

		for key in self._db: # sort alphabetically
			self._db[key].sort(cmp=cmp, key=lambda x: str.lower(x[0]))

	def get_cat (self, cat, byName = True):
		"""Returns the packages in the category.
		
		@param cat: category to return the packages from
		@type cat: string
		@param byName: selects whether to return the list sorted by name or by installation
		@type byName: boolean
		@return: list of tuples: (name, is_installed) or []
		@rtype: (string, boolean)[]"""

		try:
			if byName:
				return self._db[cat]
			else:
				inst = []
				ninst = []
				for p, i in self._db[cat]:
					if i:
						inst.append((p,i))
					else:
						ninst.append((p,i))

				return inst+ninst

		except KeyError: # cat is in category list - but not in portage
			debug("Catched KeyError =>", cat, "seems not to be an available category. Have you played with rsync-excludes?")
			return []

	def reload (self, cat):
		"""Reloads the given category.
		
		@param cat: category
		@type cat: string"""

		del self._db[cat]
		self.populate(cat+"/")

class EmergeQueue:
	"""This class manages the emerge queue."""
	
	def __init__ (self, tree = None, console = None, db = None, title_update = None):
		"""Constructor.
		
		@param tree: Tree to append all the items to.
		@type tree: Tree
		@param console: Output is shown here.
		@type console: Console
		@param db: A database instance.
		@type db: Database
		@param title_update: A function, which will be called whenever there is a title update.
		@type title_update: function(string)"""
		
		# the different queues
		self.mergequeue = [] # for emerge
		self.unmergequeue = [] # for emerge -C
		self.oneshotmerge = [] # for emerge --oneshot
		
		# the emerge process
		self.process = None

		# dictionaries with data about the packages in the queue
		self.iters = {} # iterator in the tree
		self.deps = {} # all the deps of the package
		
		# member vars
		self.tree = tree
		if self.tree and not isinstance(self.tree, Tree): raise TypeError, "tree passed is not a Tree-object"
		
		self.console = console
		if self.console and not isinstance(self.console, Console): raise TypeError, "console passed is not a Console-object"
		
		self.db = db
		self.title_update = title_update

		# our iterators pointing at the toplevels; they are set to None if we do not have a tree
		if self.tree: 
			self.emergeIt = self.tree.get_emerge_it()
			self.unmergeIt = self.tree.get_unmerge_it()
		else:
			self.emergeIt = self.unmergeIt = None

	def _get_pkg_from_cpv (self, cpv, unmask = False):
		"""Gets a L{backend.Package}-object from a cpv.

		@param cpv: the cpv to get the package for
		@type cpv: string (cpv)
		@param unmask: if True we will look for masked packages if we cannot find unmasked ones
		@type unmask: boolean
		@return: created package
		@rtype: backend.Package
		
		@raises backend.PackageNotFoundException: If no package could be found - normally it is existing but masked."""

		# for the beginning: let us create a package object - but it is not guaranteed, that it actually exists in portage
		pkg = system.new_package(cpv)
		masked = not (pkg.is_masked() or pkg.is_testing(use_keywords=True)) # we are setting this to True in case we have unmasked it already, but portage does not know this
		
		# and now try to find it in portage
		pkg = system.find_packages("="+cpv, masked = masked)
		
		if pkg: # gotcha
			pkg = pkg[0]

		elif unmask: # no pkg returned, but we are allowed to unmask it
			pkg = system.find_packages("="+cpv, masked = True)

			if not pkg:
				raise backend.PackageNotFoundException(cpv) # also not found
			else:
				pkg = pkg[0]

			if pkg.is_testing(use_keywords = True):
				pkg.set_testing(True)
			if pkg.is_masked():
				pkg.set_masked()
		
		else: # no pkg returned - and we are not allowed to unmask
			raise backend.PackageNotFoundException(cpv)
		
		return pkg
	
	def update_tree (self, it, cpv, unmask = False, oneshot = False):
		"""This updates the tree recursivly, or? Isn't it? Bjorn!

		@param it: iterator where to append
		@type it: Iterator
		@param cpv: The package to append.
		@type cpv: string (cat/pkg-ver)
		@param unmask: True if we are allowed to look for masked packages
		@type unmask: boolean
		@param oneshot: True if we want to emerge is oneshot
		@type oneshot: boolean
		
		@raises backend.BlockedException: When occured during dependency-calculation.
		@raises backend.PackageNotFoundException: If no package could be found - normally it is existing but masked."""
		
		if cpv in self.deps:
			return # in list already and therefore it's already in the tree too	
		
		# try to find an already installed instance
		update = False
		uVersion = None
		try:
			pkg = self._get_pkg_from_cpv(cpv, unmask)
			if not pkg.is_installed():
				old = system.find_installed_packages(pkg.get_slot_cp())
				if old: 
					old = old[0] # assume we have only one there
					update = True
					uVersion = old.get_version()

		except backend.PackageNotFoundException, e: # package not found / package is masked -> delete current tree and re-raise the exception
			if self.tree.iter_has_parent(it):
				while self.tree.iter_has_parent(it):
					it = self.tree.parent_iter(it)
				self.remove_with_children(it)
			raise

		# add iter
		subIt = self.tree.append(it, self.tree.build_append_value(cpv, oneshot = oneshot, update = update, version = uVersion))
		self.iters.update({cpv: subIt})
		
		# get dependencies
		deps = pkg.get_dep_packages() # this might raise a BlockedException
		self.deps.update({cpv : deps})
		
		# recursive call
		for d in deps:
			try:
				self.update_tree(subIt, d, unmask)
			except backend.BlockedException, e: # BlockedException occured -> delete current tree and re-raise exception
				debug("Something blocked:", e[0])
				self.remove_with_children(subIt)
				raise
		
	def append (self, cpv, unmerge = False, update = False, forceUpdate = False, unmask = False, oneshot = False):
		"""Appends a cpv either to the merge queue or to the unmerge-queue.
		Also updates the tree-view.
		
		@param cpv: Package to add
		@type cpv: string (cat/pkg-ver)
		@param unmerge: Set to True if you want to unmerge this package - else False.
		@type unmerge: boolean		
		@param update: Set to True if a package is going to be updated (e.g. if the use-flags changed).
		@type update: boolean
		@param forceUpdate: Set to True if the update should be forced.
		@type forceUpdate: boolean
		@param unmask: True if we are allowed to look for masked packages
		@type unmask: boolean
		@param oneshot: True if this package should not be added to the world-file.
		@type oneshot: boolean
		
		@raises portato.backend.PackageNotFoundException: if trying to add a package which does not exist"""
		
		if not unmerge: # emerge
			# insert dependencies
			pkg = self._get_pkg_from_cpv(cpv, unmask)
			deps = pkg.get_dep_packages()
			
			if update:
				if not forceUpdate and cpv in self.deps and deps == self.deps[cpv]:
					return # nothing changed - return
				else:
					hasBeenInQueue = (cpv in self.mergequeue or cpv in self.oneshotmerge)
					parentIt = self.tree.parent_iter(self.iters[cpv])

					# delete it out of the tree - but NOT the changed flags
					self.remove_with_children(self.iters[cpv], removeNewFlags = False)
					
					if hasBeenInQueue: # package has been in queue before
						self._queue_append(cpv, oneshot)
					
					self.update_tree(parentIt, cpv, unmask, oneshot = oneshot)
			else: # not update
				self._queue_append(cpv, oneshot)
				if self.emergeIt: 
					self.update_tree(self.emergeIt, cpv, unmask, oneshot = oneshot)
			
		else: # unmerge
			self.unmergequeue.append(cpv)
			if self.unmergeIt: # update tree
				self.tree.append(self.unmergeIt, self.tree.build_append_value(cpv))

	def _queue_append (self, cpv, oneshot = False):
		"""Convenience function appending a cpv either to self.mergequeue or to self.oneshotmerge.

		@param cpv: cpv to add
		@type cpv: string (cpv)
		@param oneshot: True if this package should not be added to the world-file.
		@type oneshot: boolean"""

		if not oneshot:
			if cpv not in self.mergequeue:
				self.mergequeue.append(cpv)
		else:
			if cpv not in self.oneshotmerge:
				self.oneshotmerge.append(cpv)
	
	def _update_packages(self, packages):
		"""This updates the packages-list. It simply makes the db to rebuild the specific category.
		
		@param packages: The packages which we emerged.
		@type packages: list of cpvs"""
		
		old_title = self.console.get_window_title()
		while self.process and self.process.poll() is None:
			if self.title_update : 
				title = self.console.get_window_title()
				if title != old_title:
					self.title_update(title)
				time.sleep(0.5)

		self.process = None

		if self.title_update: self.title_update(None)

		@plugin.hook("after_emerge", packages)
		def update_packages():
			for p in packages:
				if p in ["world", "system"]: continue
				cat = system.split_cpv(p)[0] # get category
				self.db.reload(cat)
				debug("Category %s refreshed" % cat)

		update_packages()

	def _emerge (self, options, packages, it, command = None):
		"""Calls emerge and updates the terminal.
		
		@param options: options to send to emerge
		@type options: list
		@param packages: packages to emerge
		@type packages: list
		@param it: Iterators which point to these entries whose children will be removed after completion.
		@type it: Iterator[]
		@param command: the command to execute - default is "/usr/bin/python /usr/bin/emerge"
		@type command: string[]"""

		@plugin.hook("emerge", packages, command)
		def sub_emerge(command):
			if command is None:
				command = system.get_merge_command()

			# open tty
			(master, slave) = pty.openpty()
			self.console.set_pty(master)
			
			# start emerge
			self.process = Popen(command+options+packages, stdout = slave, stderr = STDOUT, shell = False, env = system.get_environment())
			
			# start thread waiting for the stop of emerge
			if packages:
				Thread(name="Emerge-Thread", target=self._update_packages, args=(packages+self.deps.keys(),)).start()
			
			# remove
			for i in it:
				self.remove_with_children(i)

		sub_emerge(command)

	def emerge (self, force = False, options = None):
		"""Emerges everything in the merge-queue.
		
		@param force: If False, '-pv' is send to emerge. Default: False.
		@type force: boolean
		@param options: Additional options to send to the emerge command
		@type options: string[]"""
		
		def prepare(queue):
			"""Prepares the list of iterators and the list of packages."""
			list = []
			its = []
			for k in queue:
				list += ["="+k]
				its.append(self.iters[k])

			return list, its

		# oneshot-queue
		if len(self.oneshotmerge) != 0:
			# prepare package-list for oneshot
			list, its = prepare(self.oneshotmerge)
			
			s = system.get_oneshot_option()
			if not force: s += system.get_pretend_option()
			if options is not None: s += options
			
			self._emerge(s, list, its)
		
		# normal queue
		if len(self.mergequeue) != 0:
			# prepare package-list
			list, its = prepare(self.mergequeue)

			s = []
			if not force: s = system.get_pretend_option()
			if options is not None: s += options
		
			self._emerge(s, list, its)

	def unmerge (self, force = False, options = None):
		"""Unmerges everything in the umerge-queue.

		@param force: If False, '-pv' is send to emerge. Default: False.
		@type force: boolean
		@param options: Additional options to send to the emerge command
		@type options: string[]"""
		
		if len(self.unmergequeue) == 0: return # nothing in queue

		list = self.unmergequeue[:] # copy the unmerge-queue
		
		# set options
		s = system.get_unmerge_option()
		if not force: s += system.get_pretend_option()
		if options is not None: s += options
		
		self._emerge(s,list, [self.unmergeIt])

	def update_world(self, force = False, newuse = False, deep = False, options = None):
		"""Does an update world. newuse and deep are the arguments handed to emerge.

		@param force: If False, '-pv' is send to emerge. Default: False.
		@type force: boolean
		@param newuse: If True, append newuse options
		@type force: boolean
		@param deep: If True, append deep options
		@type deep: boolean
		@param options: Additional options to send to the emerge command
		@type options: string[]"""

		opts = system.get_update_option()

		if newuse: opts += system.get_newuse_option()
		if deep: opts += system.get_deep_option()
		if not force: opts += system.get_pretend_option()
		if options is not None: opts += options

		self._emerge(opts, ["world"], [self.emergeIt])

	def sync (self, command = None):
		"""Calls "emerge --sync".
		
		@param command: command to execute to sync. If None "emerge --sync" is taken.
		@type command: string[]"""

		if command is None:
			command = system.get_sync_command()
		
		def threaded_sync (cmd):
			ret = self.process.wait()
			self.process = None
			if ret == 0:
				__sync(cmd, False)
		
		def __sync(cmd, startThread = True):
			try:
				idx = cmd.index("&&")
			except ValueError: # no && in there -> normal behavior
				self._emerge([],[],[], command = cmd)
			else:
				self._emerge([],[],[], command = cmd[:idx])

				if startThread:
					Thread(name = "SyncThread", target = threaded_sync, args = (cmd[idx+1:],)).start()
				else:
					threaded_sync(cmd[idx+1:])

		__sync(command)


	def kill_emerge (self):
		"""Kills the emerge process."""
		if self.process is not None:
			try:
				os.kill(self.process.pid, signal.SIGTERM)
				debug("Process should be killed")
				os.kill(self.process.pid, signal.SIGKILL) # to be sure
			except AttributeError:
				debug("AttributeError occured ==> process not exisiting - ignore")
			except OSError:
				debug("OSError occured ==> process already stopped - ignore")

			self.process = None

	def remove_with_children (self, it, removeNewFlags = True):
		"""Convenience function which removes all children of an iterator and than the iterator itself.

		@param it: The iter which to remove.
		@type it: Iterator
		@param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
		@type removeNewFlags: boolean"""

		self.remove_children(it, removeNewFlags)
		self.remove(it, removeNewFlags)

	def remove_children (self, parentIt, removeNewFlags = True):
		"""Removes all children of a given parent TreeIter recursivly.
		
		@param parentIt: The iter from which to remove all children.
		@type parentIt: Iterator
		@param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
		@type removeNewFlags: boolean"""

		childIt = self.tree.first_child_iter(parentIt)

		while childIt:
			if (self.tree.iter_has_children(childIt)): # recursive call
				self.remove_children(childIt, removeNewFlags)
			temp = childIt
			childIt = self.tree.next_iter(childIt)
			self.remove(temp, removeNewFlags)

	def remove (self, it, removeNewFlags = True):
		"""Removes a specific item in the tree. This does not remove the top-entries.
		
		@param it: Iterator which points to the entry we are going to remove.
		@type it: Iterator
		@param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
		@type removeNewFlags: boolean"""
		
		if self.tree.iter_has_parent(it): # NEVER remove our top stuff
			cpv = self.tree.get_value(it, self.tree.get_cpv_column())
			if self.tree.is_in_emerge(it): # Emerge
				del self.iters[cpv]
				try:
					del self.deps[cpv]
				except KeyError: # this seems to be removed due to a BlockedException - so no deps here atm ;)
					debug("Catched KeyError =>", cpv, "seems not to be in self.deps. Should be no harm in normal cases.")
				try:
					self.mergequeue.remove(cpv)
				except ValueError: # this is a dependency - ignore
					try:
						self.oneshotmerge.remove(cpv)
					except ValueError:
						debug("Catched ValueError =>", cpv, "seems not to be in merge-queue. Should be no harm.")
				
				if removeNewFlags: # remove the changed flags
					flags.remove_new_use_flags(cpv)
					flags.remove_new_masked(cpv)
					flags.remove_new_testing(cpv)
			
			else: # in Unmerge
				self.unmergequeue.remove(cpv)
			
			self.tree.remove(it)

	def is_empty (self):
		"""Checks whether the current queue is empty and not working. Therefore it looks, whether the queues are empty,
		and the process is not running.

		@returns: True if everything is empty and the process is not running.
		@rtype: bool"""

		return not (self.mergequeue or self.unmergequeue or self.oneshotmerge or self.process)
