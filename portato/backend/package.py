# -*- coding: utf-8 -*-
#
# File: portato/backend/package.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from portato.backend import *
from portato.helper import *
from portage_helper import *
import flags

import portage, portage_dep
from portage_util import unique_array

import types
import os.path

class Package:
	"""This is a class abstracting a normal package which can be installed."""

	def __init__ (self, cpv):
		"""Constructor.

		@param cpv: The cpv which describes the package to create.
		@type cpv: string (cat/pkg-ver)"""

		self._cpv = cpv
		self._scpv = portage.catpkgsplit(self._cpv)
		
		if not self._scpv:
			raise ValueError("invalid cpv: %s" % cpv)

		self._settings = settings
		self._settingslock = settingslock
		
		try:
			self._status = portage.getmaskingstatus(self.get_cpv(), settings = self._settings)
		except KeyError: # package is not located in the system
			self._status = None
	
	def is_installed(self):
		"""Returns true if this package is installed (merged)"""
		return vartree.dbapi.cpv_exists(self._cpv)

	def is_overlay(self):
		"""Returns true if the package is in an overlay."""
		dir,ovl = portage.portdb.findname2(self._cpv)
		return ovl != self._settings["PORTDIR"]

	def is_in_system (self):
		"""Returns False if the package could not be found in the portage system.

		@return: True if in portage system; else False
		@rtype: boolean"""

		return (self._status != None)

	def is_missing_keyword(self):
		"""Returns True if the package is missing the needed keyword.
		
		@return: True if keyword is missing; else False
		@rtype: boolean"""
		
		if self._status and "missing keyword" in self._status:
			return True
		return False

	def is_testing(self, allowed = False):
		"""Checks whether a package is marked as testing.
		
		@param allowed: Controls whether possible keywords are taken into account or not.
		@type allowed: boolean
		@returns: True if the package is marked as testing; else False.
		@rtype: boolean"""

		testArch = "~" + self.get_settings("ARCH")
		if not allowed: # keywords are NOT taken into account
			if testArch in self.get_env_var("KEYWORDS").split():
				return True
			return False
		
		else: # keywords are taken into account
			status = flags.new_testing_status(self.get_cpv())
			if status == None: # we haven't changed it in any way
				if self._status and testArch+" keyword" in self._status:
					return True
				return False
			else:
				return status
	
	def set_testing(self, enable = True):
		"""Sets the actual testing status of the package.
		
		@param enable: if True it is masked as stable; if False it is marked as testing
		@type enable: boolean"""
		
		flags.set_testing(self, enable)

	def remove_new_testing(self):
		"""Removes possible changed testing status."""
		
		flags.remove_new_testing(self.get_cpv())

	def is_masked (self):
		"""Returns True if either masked by package.mask or by profile.
		
		@returns: True if masked / False otherwise
		@rtype: boolean"""
		
		status = flags.new_masking_status(self.get_cpv())
		if status != None: # we have locally changed it
			if status == "masked": return True
			elif status == "unmasked": return False
			else:
				debug("BUG in flags.new_masking_status. It returns",status)
		else: # we have not touched the status
			if self._status and ("profile" in self._status or "package.mask" in self._status):
				return True
			return False

	def set_masked (self, masking = False):
		"""Sets the masking status of the package.
	
		@param masking: if True: mask it; if False: unmask it
		@type masking: boolean"""
		
		flags.set_masked(self, masked = masking)

	def remove_new_masked (self):
		"""Removes possible changed masking status."""
		
		flags.remove_new_masked(self.get_cpv())

	def get_all_use_flags (self, installed = False):
		"""Returns a list of _all_ useflags for this package, i.e. all useflags you can set for this package.
		
		@param installed: do not take the ones stated in the ebuild, but the ones it has been installed with
		@type installed: boolean

		@returns: list of use-flags
		@rtype: string[]"""

		if installed:
			tree = vartree
		else:
			tree = porttree
		
		return unique_array(self.get_env_var("IUSE", tree = tree).split())

	def get_installed_use_flags (self):
		"""Returns a list of the useflags enabled at installation time. If package is not installed, it returns an empty list.
		
		@returns: list of useflags enabled at installation time or an empty list
		@rtype: string[]"""
		
		if self.is_installed():
			uses = self.get_use_flags().split() # all set at installation time
			iuses = self.get_all_use_flags() # all you can set for the package
			set = []
			for u in iuses:
				if u in uses:
					set.append(u)
			return set
		else:
			return []
	
	def get_new_use_flags (self):
		"""Returns a list of the new useflags, i.e. these flags which are not written to the portage-system yet.

		@returns: list of flags or []
		@rtype: string[]"""

		return flags.get_new_use_flags(self)

	def get_actual_use_flags (self):
		"""This returns the result of installed_use_flags + new_use_flags. If the package is not installed, it returns only the new flags.

		@return: list of flags
		@rtype: string[]"""

		if self.is_installed():
			i_flags = self.get_installed_use_flags()
			for f in self.get_new_use_flags():
				
				if flags.invert_flag(f) in i_flags:
					i_flags.remove(flags.invert_flag(f))
				
				elif f not in i_flags:
					i_flags.append(f)
			return i_flags
		else:
			return self.get_new_flags()

	def set_use_flag (self, flag):
		"""Set a use-flag.

		@param flag: the flag to set
		@type flag: string"""
		
		flags.set_use_flag(self, flag)

	def remove_new_use_flags (self):
		"""Remove all the new use-flags."""
		
		flags.remove_new_use_flags(self)

	def get_matched_dep_packages (self):
		"""This function looks for all dependencies which are resolved. In normal case it makes only sense for installed packages, but should work for uninstalled ones too.

		@returns: unique list of dependencies resolved (with elements like "<=net-im/foobar-1.2.3")
		@rtype: string[]"""
		
		# change the useflags, because we have internally changed some, but not made them visible for portage
		newUseFlags = self.get_new_use_flags()
		actual = self.get_settings("USE").split()
		if newUseFlags:
			for u in newUseFlags:
				if u[0] == "-" and flags.invert_use_flag(u) in actual:
					actual.remove(flags.invert_use_flag(u))
				elif u not in actual:
					actual.append(u)
		
		#
		# the following stuff is mostly adapted from portage.dep_check()
		#

		depstring = self.get_env_var("RDEPEND")+" "+self.get_env_var("DEPEND")+" "+self.get_env_var("PDEPEND")
		
		# change the parentheses into lists
		mysplit = portage_dep.paren_reduce(depstring)

		# strip off these deps we don't have a flag for
		mysplit = portage_dep.use_reduce(mysplit, uselist = actual, masklist = [], matchall = False, excludeall = self.get_settings("ARCH"))

		# move the || (or) into the lists
		mysplit = portage_dep.dep_opconvert(mysplit)

		# turn virtuals into real packages
		mysplit = portage.dep_virtual(mysplit, self._settings)

		mysplit_reduced= portage.dep_wordreduce(mysplit, self._settings, vartree.dbapi, mode = None)
		
		retlist = []
		def add (list, red_list):
			"""Adds the packages to retlist."""
			for i in range(len(list)):
				if type(list[i]) == types.ListType:
					add(list[i], red_list[i])
				elif list[i] == "||": 
					continue
				else:
					if red_list[i]:
						retlist.append(list[i])

		add(mysplit, mysplit_reduced)

		return unique_array(retlist)

	def get_dep_packages (self):
		"""Returns a cpv-list of packages on which this package depends and which have not been installed yet. This does not check the dependencies in a recursive manner.

		@returns: list of cpvs on which the package depend
		@rtype: string[]

		@raises portato.BlockedException: when a package in the dependency-list is blocked by an installed one
		@raises portato.PackageNotFoundException: when a package in the dependency list could not be found in the system
		@raises portato.DependencyCalcError: when an error occured during executing portage.dep_check()"""

		dep_pkgs = [] # the package list
		
		# change the useflags, because we have internally changed some, but not made them visible for portage
		newUseFlags = self.get_new_use_flags()
		actual = self.get_settings("USE").split()
		if newUseFlags:
			for u in newUseFlags:
				if u[0] == "-" and flags.invert_use_flag(u) in actual:
					actual.remove(flags.invert_use_flag(u))
				elif u not in actual:
					actual.append(u)

		# let portage do the main stuff ;)
		# pay attention to any changes here
		deps = portage.dep_check (self.get_env_var("RDEPEND")+" "+self.get_env_var("DEPEND")+" "+self.get_env_var("PDEPEND"), vartree.dbapi, self._settings, myuse = actual, trees = trees)
		
		if not deps: # FIXME: what is the difference to [1, []] ?
			return [] 

		if deps[0] == 0: # error
			raise DependencyCalcError, deps[1]
		
		deps = deps[1]

		for dep in deps:
			if dep[0] == '!': # blocking sth
				dep = dep[1:]
				if dep != self.get_cp(): # not cpv, because a version might explicitly block another one
					blocked = find_installed_packages(dep)
					if blocked != []:
						raise BlockedException, (self.get_cpv(), blocked[0].get_cpv())
				continue # finished with the blocking one -> next

			pkg = find_best_match(dep)
			if not pkg: # try to find masked ones
				list = find_packages(dep, masked = True)
				if not list:
					raise PackageNotFoundException, dep

				list = sort_package_list(list)
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

	def get_cpv(self):
		"""Returns full Category/Package-Version string"""
		return self._cpv

	def get_cp (self):
		"""Returns the cp-string.
		
		@returns: category/package.
		@rtype: string"""
		
		return self.get_category()+"/"+self.get_name()

	def get_slot_cp (self):

		return ("%s:%s" % (self.get_cp(), self.get_env_var("SLOT")))

	def get_name(self):
		"""Returns base name of package, no category nor version"""
		return self._scpv[1]

	def get_version(self):
		"""Returns version of package, with revision number"""
		v = self._scpv[2]
		if self._scpv[3] != "r0":
			v += "-" + self._scpv[3]
		return v

	def get_category(self):
		"""Returns category of package"""
		return self._scpv[0]

	def get_settings(self, key):
		"""Returns the value of the given key for this package (useful 
		for package.* files)."""
		self._settingslock.acquire()
		self._settings.setcpv(self._cpv)
		v = self._settings[key]
		self._settingslock.release()
		return v

	def get_ebuild_path(self):
		"""Returns the complete path to the .ebuild file"""
		return portage.portdb.findname(self._cpv)

	def get_package_path(self):
		"""Returns the path to where the ChangeLog, Manifest, .ebuild files reside"""
		p = self.get_ebuild_path()
		sp = p.split("/")
		if len(sp):
			return string.join(sp[:-1],"/")

	def get_env_var(self, var, tree=""):
		"""Returns one of the predefined env vars DEPEND, RDEPEND, SRC_URI,...."""
		if tree == "":
			mytree = vartree
			if not self.is_installed():
				mytree = porttree
		else:
			mytree = tree
		r = mytree.dbapi.aux_get(self._cpv,[var])
		
		return r[0]

	def get_use_flags(self):
		if self.is_installed():
			return self.get_env_var("USE", tree = vartree)
		else: return ""

	def compare_version(self,other):
		"""Compares this package's version to another's CPV; returns -1, 0, 1"""
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
		"""This checks, whether this package matches a specific verisioning criterion - e.g.: "<=net-im/foobar-1.2".
		
		@param criterion: the criterion to match against
		@type criterion: string
		@returns: True if matches; False if not
		@rtype: boolean"""
		
		if portage.match_from_list(criterion, [self.get_cpv()]) == []:
			return False
		else:
			return True
