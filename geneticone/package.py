#!/usr/bin/python

#
# File: geneticone/package.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 Necoro d.M.
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by Necoro d.M. <necoro@necoro.net>

from geneticone import *

import gentoolkit
import portage
from portage_util import unique_array

class Package (gentoolkit.Package):
	"""This is just a subclass of the Package-class of gentoolkit."""

	def __init__ (self, cpv):
		if isinstance(cpv, gentoolkit.Package):
			cpv = cpv.get_cpv()
		gentoolkit.Package.__init__(self, cpv)
	
	def get_mask_status(self):
		'''gets the numeric mask status of a package
		can be translated as string:
		maskmodes = [ "  ", " ~", " -", "M ", "M~", "M-" ]
		(0=unmasked 1=~arch 2=-arch etc.)
		
		This method adapted from equery 0.1.4 
		Original author: Karl Trygve Kalleberg <karltk@gentoo.org>
		'''
		
		pkgmask = 0
		if self.is_masked():
			pkgmask = pkgmask + 3
		keywords = self.get_env_var("KEYWORDS").split()
		if "~" + gentoolkit.settings["ARCH"] in keywords:
			pkgmask = pkgmask + 1
		elif "-*" in keywords or "-" + gentoolkit.settings["ARCH"] in keywords:
			pkgmask = pkgmask + 2
		return pkgmask

	def get_size (self):
		return self.size()

	def get_all_useflags (self):
		"""Returns a list of _all_ useflags for this package."""
		return unique_array(self.get_env_var("IUSE").split())

	def get_all_deps (self):
		"""Returns a linearised list of all first-level dependencies for this package, on
		the form [(comparator, [use flags], cpv), ...]"""
		return unique_array(self.get_compiletime_deps()+self.get_runtime_deps()+self.get_postmerge_deps())

	def get_dep_packages (self):
		"""Returns a cpv-list of packages on which this package depends and which have not been installed yet.
		raises: BlockedException, PackageNotFoundException."""
		dep_pkgs = [] # the package list
		
		# let portage do the main stuff ;)
		# pay attention to any changes here
		deps = portage.dep_check (self.get_env_var("RDEPEND")+" "+self.get_env_var("DEPEND"), vartree.dbapi, self._settings)
		
		if not deps: # what is the difference to [1, []] ?
			return [] 

		deps = deps[1]

		for dep in deps:
			if dep[0] == '!':
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

	def own_get_dep_packages (self, old_cpv_dict = {}):
		# XXX: after having finished this, i realized, that there is already a portage function -.- ;
		# will keep this in case portage changes anything
		"""Returns a list of all packages (i.e. package-cpvs) which this package depends on and which not have been installed yet.
		Param old_cpv_dict is a {cp: version}-dictionary holding already found deps.
		Raises a BlockedException if the package is being blocked by another installed package."""
		# XXX: This won't find blocking dependencies
		# XXX: Has some problems with modular X (this has a very strange ebuild) ... we should enhance _parse_deps
		print "Actual: "+self._cpv # debug output
		
		uses = [] # list of actual useflags / useflags the package has been installed with
		dep_packages = [] # list of packages returned
		dep_cpv_dict = {} # all dependencies are inserted here
		
		# get useflags
		if self.is_installed():
			uses = self.get_set_useflags()
		else:
			uses = self.get_settings("USE")
		
		# cycle through dependencies
		for (comp, flags, dep_cpv) in self.get_all_deps():

			# find blocking packages
			if comp and comp[0] == '!':
				blocked = find_installed_packages(comp[1:]+dep_cpv)
				if blocked != []:
					raise BlockedException, blocked[0].get_cpv()
				else: # next flag
					continue
			
			# look whether this package is really required
			needDep = True
			for flag in flags:
				if (flag[0] == '!' and flag[1:] in uses) or (flag[0] != '!' and flag not in uses):
					needDep = False
					break

			if needDep: # it is ...
				if find_installed_packages(comp+dep_cpv) == []: # ... and not installed yet
					d = find_best_match(comp+dep_cpv)
					if not d: # no package found
						raise PackageNotFoundException, dep_cpv
					if d.get_cp() not in old_cpv_dict: # ... and not found already by an other package
						dep_cpv_dict[d.get_cp()] = d.get_version()
						print "Dep: "+d.get_cpv() # debug
						dep_packages.append(d.get_cpv())
		
		for dep in dep_packages: # find dependencies for each package
			old_cpv_dict.update(dep_cpv_dict)
			old_cpv_dict.update({self.get_cp() : self.get_version()})
			dep_packages += find_packages("="+dep)[0].own_get_dep_packages(old_cpv_dict)

		return unique_array(dep_packages)

	def get_set_useflags (self):
		"""Returns a list of the useflags enabled at installation time. If package is not installed, it returns an empty list."""
		if self.is_installed():
			uses = self.get_use_flags().split()
			iuses = self.get_all_useflags()
			set = []
			for u in iuses:
				if u in uses:
					set.append(u)
			return set
		else:
			return []

	def get_cp (self):
		"""Returns category/package."""
		return self.get_category()+"/"+self.get_name()

	def is_masked (self):
		"""Returns True if either masked by package.mask or by profile."""
		# XXX: Better solution than string comparison?
		status = portage.getmaskingstatus(self._cpv)
		if "profile" in status or "package.mask" in status:
			return True
		return False

	def matches (self, criterion):
		"""This checks, whether this package matches a specific verisioning criterion - e.g.: "<=net-im/foobar-1.2"."""
		if portage.match_from_list(criterion, [self.get_cpv()]) == []:
			return False
		else:
			return True

	def _parse_deps(self,deps,curuse=[],level=0):
		"""Modified method "_parse_deps" of gentoolkit.Package.
		Do NOT ignore blocks."""
		# store (comparator, [use predicates], cpv)
		r = []
		comparators = ["~","<",">","=","<=",">="]
		end = len(deps)
		i = 0
		while i < end:
			blocked = False
			tok = deps[i]
			if tok == ')':
				return r,i
			if tok[-1] == "?":
				tok = tok.replace("?","")
				sr,l = self._parse_deps(deps[i+2:],curuse=curuse+[tok],level=level+1)
				r += sr
				i += l + 3
				continue
			if tok == "||":
				sr,l = self._parse_deps(deps[i+2:],curuse,level=level+1)
				r += sr
				i += l + 3
				continue
			# conjonction, like in "|| ( ( foo bar ) baz )" => recurse
			if tok == "(":
				sr,l = self._parse_deps(deps[i+1:],curuse,level=level+1)
				r += sr
				i += l + 2
				continue
			# pkg block "!foo/bar" => ignore it
			if tok[0] == "!":
				#i += 1
				#continue
				blocked = True # added
				tok = tok[1:] # added
			# pick out comparator, if any
			cmp = ""
			for c in comparators:
				if tok.find(c) == 0:
					cmp = c
					if blocked: cmp = "!"+cmp # added
			tok = tok[len(cmp):]
			r.append((cmp,curuse,tok))
			i += 1
		return r,i
