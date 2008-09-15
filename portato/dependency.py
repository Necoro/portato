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

from collections import defaultdict

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
        self.flags = defaultdict(UseDependency)
        self._ors = []
        self._subs = []

    def is_empty (self):
        return not (self.deps or self.flags or self._ors or self._subs)

    empty = property(is_empty)
    
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

    def add_or (self):
        o = OrDependency()
        self._ors.append(o)
        return o

    def add_sub (self):
        return self

    def add_flag (self, flag):
        """
        Adds a new useflag to this tree.
        For convenience the newly created sub-tree is returned.

        :param flag: the new flag
        :rtype: `DependencyTree`
        """

        return self.flags[flag] # it's a defaultdict

    def parse (self, deps):
        it = iter(deps)
        for dep in it:
            if dep[-1] == "?":
                ntree = self.add_flag(dep[:-1])
                n = it.next()
                if not hasattr(n, "__iter__"):
                    n = [n]
                ntree.parse(n)
            
            elif dep == "||":
                n = it.next() # skip
                if not hasattr(n, "__iter__"):
                    n = [n]
                
                self.add_or().parse(n)

            elif isinstance(dep, list):
                self.add_sub().parse(dep)
            
            else:
                self.add(dep)

    def get_list(self, l):
        for d in l[:]:
            if d.is_empty():
                l.remove(d)
            else:
                yield d

    def get_ors (self):
        return self.get_list(self._ors)

    def get_subs (self):
        return self.get_list(self._subs)

    ors = property(get_ors)
    subs = property(get_subs)

class OrDependency (DependencyTree):
    def add_sub (self):
        s = DependencyTree()
        self._subs.append(s)
        return s

class UseDependency (DependencyTree):
    pass
