# -*- coding: utf-8 -*-
#
# File: portato/backend/portage/package.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from portato.helper import *
from portato.backend.exceptions import *
from portato.backend import flags, Package, system

import portage, portage_dep
from portage_util import unique_array

import os.path

class PortagePackage (Package):
	"""This is a class abstracting a normal package which can be installed for the portage-system."""

	def __init__ (self, cpv):
		"""Constructor.

		@param cpv: The cpv which describes the package to create.
		@type cpv: string (cat/pkg-ver)"""

		Package.__init__(self, cpv)
		self._settings = system.settings
		self._settingslock = system.settings.settingslock

		self._trees = system.settings.trees

		self.forced_flags = set()
		self.forced_flags.update(self._settings.settings.usemask)
		self.forced_flags.update(self._settings.settings.useforce)
		
		try:
			self._status = portage.getmaskingstatus(self.get_cpv(), settings = self._settings.settings)
		except KeyError: # package is not located in the system
			self._status = None
	
	def is_installed(self):
		return self._settings.vartree.dbapi.cpv_exists(self._cpv)

	def is_overlay(self):
		dir,ovl = self._settings.porttree.dbapi.findname2(self._cpv)
		return ovl != self._settings.settings["PORTDIR"]

	def is_in_system (self):
		return (self._status != None)

	def is_missing_keyword(self):
		if self._status and "missing keyword" in self._status:
			return True
		return False

	def is_testing(self, use_keywords = False):
		testArch = "~" + self.get_global_settings("ARCH")
		if not use_keywords: # keywords are NOT taken into account
			if testArch in self.get_package_settings("KEYWORDS").split():
				return True
			return False
		
		else: # keywords are taken into account
			status = flags.new_testing_status(self.get_cpv())
			if status is None: # we haven't changed it in any way
				if self._status and testArch+" keyword" in self._status:
					return True
				return False
			else:
				return status
	
	def is_masked (self, use_changed = True):
		
		if use_changed:
			status = flags.new_masking_status(self.get_cpv())
			if status != None: # we have locally changed it
				if status == "masked": return True
				elif status == "unmasked": return False
				else:
					debug("BUG in flags.new_masking_status. It returns", status, error = True)
			else: # we have not touched the status
				if self._status and ("profile" in self._status or "package.mask" in self._status):
					return True
				return False
		else: # we want the original portage value XXX: bug if masked by user AND by system
			
			# get the normal masked ones
			if self._status and ("profile" in self._status or "package.mask" in self._status):
				if not flags.is_locally_masked(self, changes = False): # assume that if it is locally masked, it is not masked by the system
					return True
			else: # more difficult: get the ones we unmasked, but are masked by the system
				try:
					masked = self._settings.settings.pmaskdict[self.get_cp()]
				except KeyError: # key error: not masked
					return False

				for cpv in masked:
					if self.matches(cpv):
						if not flags.is_locally_masked(self, changes = False): # assume that if it is locally masked, it is not masked by the system
							return True
						else:
							return False

			return False

	def get_all_use_flags (self, installed = False):
		if installed or not self.is_in_system():
			tree = self._settings.vartree
		else:
			tree = self._settings.porttree
		
		return list(set(self.get_package_settings("IUSE", tree = tree).split()).difference(self.forced_flags))

	def get_matched_dep_packages (self, depvar):
		# change the useflags, because we have internally changed some, but not made them visible for portage
		newUseFlags = self.get_new_use_flags()
		actual = self.get_global_settings("USE").split()
		if newUseFlags:
			for u in newUseFlags:
				if u[0] == "-" and flags.invert_use_flag(u) in actual:
					actual.remove(flags.invert_use_flag(u))
				elif u not in actual:
					actual.append(u)
		
		depstring = ""
		for d in depvar:
			depstring += self.get_package_settings(d)+" "

		portage_dep._dep_check_strict = False
		deps = portage.dep_check(depstring, None, self._settings.settings, myuse = actual, trees = self._trees)
		portage_dep._dep_check_strict = True

		if not deps: # FIXME: what is the difference to [1, []] ?
			return [] 

		if deps[0] == 0: # error
			raise DependencyCalcError, deps[1]
		
		deps = deps[1]

		retlist = []
		
		for d in deps:
			if not d[0] == "!":
				retlist.append(d)

		return retlist

	def get_dep_packages (self, depvar = ["RDEPEND", "PDEPEND", "DEPEND"]):
		dep_pkgs = [] # the package list
		
		# change the useflags, because we have internally changed some, but not made them visible for portage
		newUseFlags = self.get_new_use_flags()
		actual = self.get_global_settings("USE").split()
		if newUseFlags:
			for u in newUseFlags:
				if u[0] == "-" and flags.invert_use_flag(u) in actual:
					actual.remove(flags.invert_use_flag(u))
				elif u not in actual:
					actual.append(u)

		depstring = ""
		for d in depvar:
			depstring += self.get_package_settings(d, tree=self._settings.porttree)+" "

		# let portage do the main stuff ;)
		# pay attention to any changes here
		deps = portage.dep_check (depstring, self._settings.vartree.dbapi, self._settings.settings, myuse = actual, trees = self._trees)
		
		if not deps: # FIXME: what is the difference to [1, []] ?
			return [] 

		if deps[0] == 0: # error
			raise DependencyCalcError, deps[1]
		
		deps = deps[1]

		for dep in deps:
			if dep[0] == '!': # blocking sth
				dep = dep[1:]
				if dep != self.get_cp(): # not cpv, because a version might explicitly block another one
					blocked = system.find_installed_packages(dep)
					if blocked != []:
						raise BlockedException, (self.get_cpv(), blocked[0].get_cpv())
				continue # finished with the blocking one -> next

			pkg = system.find_best_match(dep)
			if not pkg: # try to find masked ones
				list = system.find_packages(dep, masked = True)
				if not list:
					raise PackageNotFoundException, dep

				list = system.sort_package_list(list)
				done = False
				for i in range(len(list)-1,0,-1):
					p = list[i]
					if not p.is_masked():
						dep_pkgs.append(p.get_cpv())
						done = True
						break
				if not done:
					dep_pkgs.append(list[-1].get_cpv())
			else:
				dep_pkgs.append(pkg.get_cpv())

		return dep_pkgs

	def get_global_settings(self, key):
		self._settingslock.acquire()
		self._settings.settings.setcpv(self._cpv)
		v = self._settings.settings[key]
		self._settingslock.release()
		return v

	def get_ebuild_path(self):
		return self._settings.porttree.dbapi.findname(self._cpv)

	def get_package_settings(self, var, tree = None):
		if not tree:
			mytree = self._settings.vartree
			if not self.is_installed():
				mytree = self._settings.porttree
		else:
			mytree = tree
		r = mytree.dbapi.aux_get(self._cpv,[var])
		
		return r[0]

	def get_use_flags(self):
		if self.is_installed():
			return self.get_package_settings("USE", tree = self._settings.vartree)
		else: return ""

	def compare_version(self,other):
		v1 = self._scpv
		v2 = portage.catpkgsplit(other.get_cpv())
		# if category is different
		if v1[0] != v2[0]:
			return cmp(v1[0],v2[0])
		# if name is different
		elif v1[1] != v2[1]:
			return cmp(v1[1],v2[1])
		# Compare versions
		else:
			return portage.pkgcmp(v1[1:],v2[1:])

	def matches (self, criterion):
		if portage.match_from_list(criterion, [self.get_cpv()]) == []:
			return False
		else:
			return True
