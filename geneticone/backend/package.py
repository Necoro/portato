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

import gentoolkit
import portage
from portage_util import unique_array

class Package (gentoolkit.Package):
	"""This is a subclass of the gentoolkit.Package-class which a lot of additional functionality we need in Genetic/One."""

	def __init__ (self, cpv):
		"""Constructor.

		@param cpv: The cpv or gentoolkit.Package which describes the package to create.
		@type cpv: string (cat/pkg-ver) or gentoolkit.Package-object."""

		if isinstance(cpv, gentoolkit.Package):
			cpv = cpv.get_cpv()
		gentoolkit.Package.__init__(self, cpv)
	
	def get_mask_status(self):
		"""Gets the numeric mask status of a package. The return value can be translated as a string when taking the following list of modes: [ "  ", " ~", " -", "M ", "M~", "M-" ]

		This method adapted from equery 0.1.4 
		Original author: Karl Trygve Kalleberg <karltk@gentoo.org>

		@returns: mask status
		@rtype: int"""
		
		pkgmask = 0
		if self.is_masked():
			pkgmask = pkgmask + 3
		keywords = self.get_env_var("KEYWORDS").split()
		if "~" + gentoolkit.settings["ARCH"] in keywords:
			pkgmask = pkgmask + 1
		elif "-*" in keywords or "-" + gentoolkit.settings["ARCH"] in keywords:
			pkgmask = pkgmask + 2
		return pkgmask

	def is_masked (self):
		"""Returns True if either masked by package.mask or by profile.
		@returns: mask-status
		@rtype: boolean"""
		# XXX: Better solution than string comparison?
		status = flags.new_masking_status(self.get_cpv())
		if status != None:
			if status == "masked": return True
			elif status == "unmasked": return False
			else:
				debug("BUG in flags.new_masking_status. It returns "+status)
		else:
			status = portage.getmaskingstatus(self._cpv, settings = gentoolkit.settings)
			if "profile" in status or "package.mask" in status:
				return True
			return False

	def set_masked (self, masking = False):
		flags.set_masked(self, masked = masking)

	def remove_new_masked (self):
		flags.remove_new_masked(self.get_cpv())

	def get_all_use_flags (self):
		"""Returns a list of _all_ useflags for this package, i.e. all useflags you can set for this package.
		
		@returns: list of use-flags
		@rtype: list"""

		return unique_array(self.get_env_var("IUSE").split())

	def get_installed_use_flags (self):
		"""Returns a list of the useflags enabled at installation time. If package is not installed, it returns an empty list.
		
		@returns: list of useflags enabled at installation time or an empty list
		@rtype: list"""
		if self.is_installed():
			uses = self.get_use_flags().split()
			iuses = self.get_all_use_flags()
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
		@rtype: list"""
		return flags.get_new_use_flags(self)

	def get_actual_use_flags (self):
		"""This returns the result of installed_use_flags + new_use_flags. If the package is not installed, it returns only the new flags.

		@return: list of flags
		@rtype: list"""

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

	def get_dep_packages (self):
		"""Returns a cpv-list of packages on which this package depends and which have not been installed yet. This does not check the dependencies in a recursive manner.

		@returns: list of cpvs on which the package depend
		@rtype: list
		@raises geneticone.BlockedException: when a package in the dependency-list is blocked by an installed one
		@raises geneticone.PackageNotFoundException: when a package in the dependency list could not be found in the system
		@raises geneticone.DependencyCalcError: when an error occured during executing portage.dep_check()"""

		dep_pkgs = [] # the package list
		
		# check whether we got use-flags which are not visible for portage yet
		newUseFlags = self.get_new_use_flags()
		actual = self.get_settings("USE").split()
		if newUseFlags:
			depUses = []
			for u in newUseFlags:
				if u[0] == "-" and flags.invert_use_flag(u) in actual:
					actual.remove(flags.invert_use_flag(u))
				elif u not in actual:
					actual.append(u)

		# let portage do the main stuff ;)
		# pay attention to any changes here
		deps = portage.dep_check (self.get_env_var("RDEPEND")+" "+self.get_env_var("DEPEND")+" "+self.get_env_var("PDEPEND"), vartree.dbapi, self._settings, myuse = actual)
		
		if not deps: # what is the difference to [1, []] ?
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
			if not dep:
				raise PackageNotFoundException, dep
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
		@type criterion: string"""
		if portage.match_from_list(criterion, [self.get_cpv()]) == []:
			return False
		else:
			return True
#
# OBSOLETE DEPENDENCY-CALCULATION-METHODS - kept in the case the above ones do not work
#

	#def own_get_dep_packages (self, old_cpv_dict = {}):
	#	# XXX: after having finished this, i realized, that there is already a portage function -.- ;
	#	"""Returns a list of all packages (i.e. package-cpvs) which this package depends on and which not have been installed yet.
	#	Param old_cpv_dict is a {cp: version}-dictionary holding already found deps.
	#	Raises a BlockedException if the package is being blocked by another installed package."""
	#	# XXX: This won't find blocking dependencies
	#	# XXX: Has some problems with modular X (this has a very strange ebuild) ... we should enhance _parse_deps
	#	print "Actual: "+self._cpv # debug output
	#	
	#	uses = [] # list of actual useflags / useflags the package has been installed with
	#	dep_packages = [] # list of packages returned
	#	dep_cpv_dict = {} # all dependencies are inserted here
	#	
	#	# get useflags
	#	if self.is_installed():
	#		uses = self.get_installed_use_flags()
	#	else:
	#		uses = self.get_settings("USE")
	#	
	#	# cycle through dependencies
	#	for (comp, flags, dep_cpv) in self.get_all_deps():

	#		# find blocking packages
	#		if comp and comp[0] == '!':
	#			blocked = find_installed_packages(comp[1:]+dep_cpv)
	#			if blocked != []:
	#				raise BlockedException, blocked[0].get_cpv()
	#			else: # next flag
	#				continue
	#		
	#		# look whether this package is really required
	#		needDep = True
	#		for flag in flags:
	#			if (flag[0] == '!' and flag[1:] in uses) or (flag[0] != '!' and flag not in uses):
	#				needDep = False
	#				break

	#		if needDep: # it is ...
	#			if find_installed_packages(comp+dep_cpv) == []: # ... and not installed yet
	#				d = find_best_match(comp+dep_cpv)
	#				if not d: # no package found
	#					raise PackageNotFoundException, dep_cpv
	#				if d.get_cp() not in old_cpv_dict: # ... and not found already by an other package
	#					dep_cpv_dict[d.get_cp()] = d.get_version()
	#					print "Dep: "+d.get_cpv() # debug
	#					dep_packages.append(d.get_cpv())
	#	
	#	for dep in dep_packages: # find dependencies for each package
	#		old_cpv_dict.update(dep_cpv_dict)
	#		old_cpv_dict.update({self.get_cp() : self.get_version()})
	#		dep_packages += find_packages("="+dep)[0].own_get_dep_packages(old_cpv_dict)

	#	return unique_array(dep_packages)

	#def get_all_deps (self):
	#	"""Returns a linearised list of all first-level dependencies for this package, on
	#	the form [(comparator, [use flags], cpv), ...]"""
	#	return unique_array(self.get_compiletime_deps()+self.get_runtime_deps()+self.get_postmerge_deps())

	#def _parse_deps(self,deps,curuse=[],level=0):
	#	"""Modified method "_parse_deps" of gentoolkit.Package.
	#	Do NOT ignore blocks."""
	#	# store (comparator, [use predicates], cpv)
	#	r = []
	#	comparators = ["~","<",">","=","<=",">="]
	#	end = len(deps)
	#	i = 0
	#	while i < end:
	#		blocked = False
	#		tok = deps[i]
	#		if tok == ')':
	#			return r,i
	#		if tok[-1] == "?":
	#			tok = tok.replace("?","")
	#			sr,l = self._parse_deps(deps[i+2:],curuse=curuse+[tok],level=level+1)
	#			r += sr
	#			i += l + 3
	#			continue
	#		if tok == "||":
	#			sr,l = self._parse_deps(deps[i+2:],curuse,level=level+1)
	#			r += sr
	#			i += l + 3
	#			continue
	#		# conjonction, like in "|| ( ( foo bar ) baz )" => recurse
	#		if tok == "(":
	#			sr,l = self._parse_deps(deps[i+1:],curuse,level=level+1)
	#			r += sr
	#			i += l + 2
	#			continue
	#		# pkg block "!foo/bar" => ignore it
	#		if tok[0] == "!":
	#			#i += 1
	#			#continue
	#			blocked = True # added
	#			tok = tok[1:] # added
	#		# pick out comparator, if any
	#		cmp = ""
	#		for c in comparators:
	#			if tok.find(c) == 0:
	#				cmp = c
	#				if blocked: cmp = "!"+cmp # added
	#		tok = tok[len(cmp):]
	#		r.append((cmp,curuse,tok))
	#		i += 1
	#	return r,i
