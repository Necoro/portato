# -*- coding: utf-8 -*-
#
# File: portato/dependency.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

"""
Provides classes for the presentation of dependencies.
"""

from __future__ import absolute_import, with_statement
__docformat__ = "restructuredtext"


from .helper import debug
from .backend import system

class Dependency (object):

	"""
	A simple dependency as it also is noted inside ebuilds.

	:IVariables:

		dep : string
			The dependency string. It is immutable.

		satisfied : boolean
			Is this dependency satisfied?
	"""

	def __init__ (self, dep):
		"""
		Creates a dependency out of a dep string.

		:param dep: dependency string
		:type dep: string
		"""
		self._dep = dep

	def is_satisfied (self):
		"""
		Checks if this dependency is satisfied.

		:rtype: boolean
		"""
		return system.find_best_match(self.dep, only_cpv = True, only_installed = True) is not None

	def __cmp__ (self, b):
		return cmp(self.dep, b.dep)

	def __hash__ (self):
		return hash(self.dep)

	def __str__ (self):
		return "<Dependency '%s'>" % self.dep

	__repr__ = __str__

	@property
	def dep (self):
		return self._dep

	satisfied = property(is_satisfied)

class OrDependency (Dependency):
	"""
	Dependency representing an "or".
	
	:note: Order is important. ``|| ( a b )`` != ``|| ( b a )``

	:IVariables:

		dep : tuple(`Dependency`,...)
			The dependencies. The tuple and the dependencies are immutable.
	"""

	def __init__ (self, deps):
		"""
		Creates an or-dependency out of a list (or tuple) of deps.

		:param deps: The or'ed dependencies.
		:type deps: iter<string>
		"""

		_dep = []
		for dep in deps:
			if not hasattr(dep, "__iter__"):
				assert not dep.endswith("?")
				_dep.append(Dependency(dep))
			else:
				_dep.append(AllOfDependency(dep))

		self._dep = tuple(_dep)
	
	def __str__ (self):
		return "<|| %s>" % str(self.dep)
	
	__repr__ = __str__

class AllOfDependency (Dependency):
	"""
	Dependency representing a set of packages inside "or".
	If the or is: ``|| (a ( b c ) )`` the `AllOfDependency` would be the ``( b c )``.

	:IVariables:

		dep : tuple(`Dependency`,...)
			The dependencies . The tuple and the deps are immutable.
	"""

	def __init__ (self, deps):
		"""
		Creates an or-dependency out of a list (or tuple) of deps.

		:param deps: The dependencies.
		:type deps: iter<string>
		"""

		self._dep = tuple(Dependency(dep) for dep in deps)

	def __str__ (self):
		return "<ALL %s>" % str(self.dep)
	
	__repr__ = __str__

class DependencyTree (object):

	"""
	The DependencyTree shows all dependencies for a package and shows which useflags want which dependencies.

	:IVariables:

		deps : set(`Dependency`)
			The list of dependencies which are not dependent on a useflag.

		flags : string -> `DependencyTree`
			Holds the additional dependency trees per useflag.
	"""

	def __init__ (self):

		self.deps = set()
		self.flags = {}

	def add (self, dep, *moredeps):
		"""
		Adds one or more normal dependencies to the tree.

		:Parameters:

			dep : string
				A dependency string.

			moredeps
				More parameters are allowed :)
		"""
		self.deps.add(Dependency(dep))

		for dep in moredeps:
			self.deps.add(Dependency(dep))

	def add_or (self, orlist):
		"""
		Adds a list of dependencies, which are or'ed.

		:param orlist: the dependency list
		:type orlist: iter<string>
		"""
		self.deps.add(OrDependency(orlist))

	def add_flag (self, flag):
		"""
		Adds a new useflag to this tree.
		For convenience the newly created sub-tree is returned.

		:param flag: the new flag
		:rtype: `DependencyTree`
		"""
		if not flag in self.flags:
			self.flags[flag] = DependencyTree()

		return self.get_flag_tree(flag)

	def get_flag_tree (self, flag):
		"""
		Returns the sub-tree of a specific tree.

		:raises KeyError: if the flag is not (yet) in this tree
		:rtype: `DependencyTree`
		"""
		return self.flags[flag]
