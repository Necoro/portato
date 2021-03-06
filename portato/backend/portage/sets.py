# -*- coding: utf-8 -*-
#
# File: portato/backend/portage/sets.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from future_builtins import map, filter, zip

import re
import itertools as itt

import portage

from .. import system
from ...helper import debug

class Set(object):

    def get_pkgs(self, key, is_regexp, masked, with_version, only_cpv):
        raise NotImplementedError

    def find (self, key, masked = False, with_version = True, only_cpv = False):
        if key is None: key = ""
        
        is_regexp = key == "" or ("*" in key[1:] and key[0] not in ("=","<",">","~","!"))

        try:
            t = self.get_pkgs(key, is_regexp, masked, with_version, only_cpv)
        # catch the "ambigous package" Exception
        except ValueError as e:
            if isinstance(e[0], list):
                t = set()
                for cp in e[0]:
                    t.update(self.get_pkgs(cp, is_regexp, masked, with_version, only_cpv))
            else:
                raise

        return t

class InstalledSet (Set):
    """For the moment do not use the portage-2.2 @installed set.
    It only contains the current slot-cps - and to get the cpvs
    via the PortageSet results in an infinite recursion :(."""

    def _get_regexp (self, key, with_version):
        if with_version:
            t = system.settings.vartree.dbapi.cpv_all()
        else:
            t = system.settings.vartree.dbapi.cp_all()

        if key:
            t = [x for x in t if re.search(key, x, re.I)]

        return t

    def _get_by_key (self, key, with_version):
        t = system.settings.vartree.dbapi.match(key)
        if not with_version:
            t = itt.imap(portage.cpv_getkey, t)

        return t

    def get_pkgs (self, key, is_regexp, masked, with_version, only_cpv):
        if is_regexp:
            return set(self._get_regexp(key, with_version))
        else:
            return set(self._get_by_key(key, with_version))

class TreeSet (Set):

    def get_pkgs (self, key, is_regexp, masked, with_version, only_cpv):
        if is_regexp:
            if with_version:
                t = system.settings.porttree.dbapi.cpv_all()
            else:
                t = system.settings.porttree.dbapi.cp_all()

            if key:
                t = [x for x in t if re.search(key, x, re.I)]

            return set(t)

        elif masked:
            t = system.settings.porttree.dbapi.xmatch("match-all", key)
        else:
            t = system.settings.porttree.dbapi.match(key)

        if not with_version:
            t = itt.imap(portage.dep.dep_getkey, t)

        return set(t)

class AllSet (Set):
    
    def __init__ (self):
        Set.__init__(self)
        self.tree = TreeSet()
        self.installed = InstalledSet()

    def find (self, *args, **kwargs):
        return self.tree.find(*args, **kwargs) | self.installed.find(*args, **kwargs)

class UninstalledSet (Set):

    def __init__ (self):
        Set.__init__(self)
        self.all = AllSet()
        self.installed = InstalledSet()

    def find (self, *args, **kwargs):
        return self.all.find(*args, **kwargs) - self.installed.find(*args, **kwargs)

class FilterSet (InstalledSet):

    def get_list(self):
        raise NotImplementedError
    
    def get_pkgs (self, key, is_regexp, masked, with_version, only_cpv):
        t = set()
        for pkg in self.get_list():
            if is_regexp and key:
                if not re.search(key, pkg, re.I): continue

            if not with_version:
                t.add(portage.dep.dep_getkey(pkg))
            else:
                t.update(self._get_by_key(pkg, with_version))

        return t

class PortageSet (FilterSet):
    def __init__ (self, name):
        debug("Loading portage set '%s'", name)
        self.name = name

    def get_list(self):
        return itt.imap(str, system.settings.setsconfig.getSetAtoms(self.name))

class SystemSet (FilterSet):

    def get_list(self):
        for cp in system.settings.global_settings.packages:
            if cp[0] == "*": yield cp[1:]

class WorldSet (FilterSet):

    def get_list(self):
        with open(portage.WORLD_FILE) as f:
            for cp in f:
                cp = cp.strip()
                if cp and cp[0] != "#":
                    yield cp

