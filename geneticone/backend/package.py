#
# File: geneticone/backend/package.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 Necoro d.M.
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by Necoro d.M. <necoro@necoro.net>

from geneticone.backend import *
from geneticone.helper import *
from portage_helper import *
import flags

import portage, portage_dep, gentoolkit
from portage_util import unique_array

import types

class Package (gentoolkit.Package):
	"""This is a subclass of the gentoolkit.Package-class which a lot of additional functionality we need in Genetic/One."""

	def __init__ (self, cpv):
		"""Constructor.

		@param cpv: The cpv or gentoolkit.Package which describes the package to create.
		@type cpv: string (cat/pkg-ver) or gentoolkit.Package-object."""

		if isinstance(cpv, gentoolkit.Package):
			cpv = cpv.get_cpv()
		gentoolkit.Package.__init__(self, cpv)
		try:
			self._status = portage.getmaskingstatus(self.get_cpv(), settings = gentoolkit.settings)
		except KeyError: # package is not located in the system
			self._status = None
	
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

	def get_all_use_flags (self):
		"""Returns a list of _all_ useflags for this package, i.e. all useflags you can set for this package.
		
		@returns: list of use-flags
		@rtype: string[]"""

		return unique_array(self.get_env_var("IUSE").split())

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

		@raises geneticone.BlockedException: when a package in the dependency-list is blocked by an installed one
		@raises geneticone.PackageNotFoundException: when a package in the dependency list could not be found in the system
		@raises geneticone.DependencyCalcError: when an error occured during executing portage.dep_check()"""

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
		deps = portage.dep_check (self.get_env_var("RDEPEND")+" "+self.get_env_var("DEPEND")+" "+self.get_env_var("PDEPEND"), vartree.dbapi, self._settings, myuse = actual)
		
		if not deps: # FIXME: what is the difference to [1, []] ?
			return [] 

		if deps[0] == 0: # error
			raise DependencyCalcError, deps[1]
		
		deps = deps[1]

		for dep in deps:
			if dep[0] == '!': # blocking sth
				blocked = find_installed_packages(dep[1:])
				if blocked != []:
					raise BlockedException, blocked[0].get_cpv()
				else: # next flag
					continue

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

	def get_cp (self):
		"""Returns the cp-string.
		
		@returns: category/package.
		@rtype: string"""
		
		return self.get_category()+"/"+self.get_name()

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
