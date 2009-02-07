# -*- coding: utf-8 -*-
#
# File: portato/dependency.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
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

        flags : string -> `UseDependency`
            Holds the additional dependency trees per useflag.

        ors : list(`OrDependency`)
            A list of dependency trees, which are or'ed.

        subs : list(`DependencyTree`)
            A list of subtrees.

        empty : boolean
            Is this tree empty?
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
        """
        Adds an `OrDependency` and returns the created tree.

        :rtype: `OrDependency`
        """
        o = OrDependency()
        self._ors.append(o)
        return o

    def add_sub (self):
        """
        Adds and returns a subtree.

        :rtype: `DependencyTree`
        """

        # a normal DepTree does not handle subtrees - so return self
        # this is intended to be overwritten by subclasses
        return self

    def add_flag (self, flag):
        """
        Adds a new useflag to this tree and returns the created sub-tree.

        :param flag: the new flag
        :rtype: `DependencyTree`
        """

        return self.flags[flag] # it's a defaultdict

    def parse (self, deps):
        """
        Parses the list of dependencies, as it is returned by paren_reduce, and fills the tree.
        """

        it = iter(deps)
        for dep in it:
            
            # use
            if dep[-1] == "?":
                ntree = self.add_flag(dep[:-1])
                n = it.next()
                if not hasattr(n, "__iter__"):
                    n = [n]
                ntree.parse(n)
            
            # or
            elif dep == "||":
                n = it.next() # skip
                if not hasattr(n, "__iter__"):
                    n = [n]
                
                self.add_or().parse(n)

            # sub
            elif isinstance(dep, list):
                self.add_sub().parse(dep)
            
            # normal
            else:
                self.add(dep)

    def get_non_empty(self, l):
        """
        Convenience accessor method. Returns these elements of a list, which are non-empty.
        This also removes the empty ones from the list.

        :param l: a list :)
        :rtype: iter
        """
        for d in l[:]:
            if d.is_empty():
                l.remove(d)
            else:
                yield d

    def get_ors (self):
        return self.get_non_empty(self._ors)

    def get_subs (self):
        return self.get_non_empty(self._subs)

    ors = property(get_ors)
    subs = property(get_subs)

class OrDependency (DependencyTree):
    """
    Models an or-dependency. This only overwrites `add_sub`, as sublists have a special meaning here.
    """
    def add_sub (self):
        s = DependencyTree()
        self._subs.append(s)
        return s

class UseDependency (DependencyTree):
    """
    Models an use-dependency. Nothing is overwritten.
    """
    pass
