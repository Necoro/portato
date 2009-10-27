# -*- coding: utf-8 -*-
#
# File: portato/backend/portage/system.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import re, os
import portage

from collections import defaultdict
import itertools as itt

from . import VERSION
from . import sets as syssets
from .package import PortagePackage
from .settings import PortageSettings
from ..system_interface import SystemInterface
from ...helper import debug, info, warning

class PortageSystem (SystemInterface):
    """This class provides access to the portage-system."""

    # pre-compile the RE removing the ".svn" and "CVS" entries
    unwantedPkgsRE = re.compile(r".*(\.svn|CVS)$")
    withBdepsRE = re.compile(r"--with-bdeps\s*( |=)\s*y")

    def __init__ (self):
        """Constructor."""
        self.settings = PortageSettings()
        portage.WORLD_FILE = os.path.join(self.settings.global_settings["ROOT"],portage.WORLD_FILE)

        self.use_descs = {}
        self.local_use_descs = defaultdict(dict)

        self.setmap = {
                self.SET_ALL : syssets.AllSet,
                self.SET_INSTALLED : syssets.InstalledSet,
                self.SET_UNINSTALLED : syssets.UninstalledSet,
                self.SET_TREE : syssets.TreeSet,
                "world" : syssets.WorldSet,
                "system" : syssets.SystemSet
                }

    def eapi_supported (self, eapi):
        return portage.eapi_is_supported(eapi)

    def has_set_support (self):
        return False

    def get_sets (self, description = False):
        if description:
            return (("world", "The world set."), ("system", "The system set."))
        else:
            return ("world", "system")

    def get_version (self):
        return "Portage %s" % portage.VERSION
    
    def new_package (self, cpv):
        return PortagePackage(cpv)

    def get_config_path (self):
        path = portage.USER_CONFIG_PATH

        if path[0] != "/":
            return os.path.join(self.settings.settings["ROOT"], path)
        else:
            return path

    def get_merge_command (self):
        return ["/usr/bin/python", "/usr/bin/emerge"]

    def get_sync_command (self):
        return self.get_merge_command()+["--sync"]

    def get_oneshot_option (self):
        return ["--oneshot"]

    def get_newuse_option (self):
        return ["--newuse"]

    def get_deep_option (self):
        return ["--deep"]

    def get_update_option (self):
        return ["--update"]

    def get_pretend_option (self):
        return ["--pretend", "--verbose"]

    def get_unmerge_option (self):
        return ["--unmerge"]

    def get_environment (self):
        default_opts = self.get_global_settings("EMERGE_DEFAULT_OPTS")
        opts = dict(os.environ)
        opts.update(TERM = "xterm") # emulate terminal :)
        opts.update(PAGER = "less") # force less

        if default_opts:
            opt_list = default_opts.split()
            changed = False

            for option in ["--ask", "-a", "--pretend", "-p"]:
                if option in opt_list:
                    opt_list.remove(option)
                    changed = True
            
            if changed:
                opts.update(EMERGE_DEFAULT_OPTS = " ".join(opt_list))

        return opts

    def cpv_matches (self, cpv, criterion):
        if portage.match_from_list(criterion, [cpv]) == []:
            return False
        else:
            return True

    def with_bdeps(self):
        """Returns whether the "--with-bdeps" option is set to true.

        @returns: the value of --with-bdeps
        @rtype: boolean
        """

        settings = self.get_global_settings("EMERGE_DEFAULT_OPTS").split()
        for s in settings:
            if self.withBdepsRE.match(s):
                return True

        return False

    def find_lambda (self, name):
        """Returns the function needed by all the find_all_*-functions. Returns None if no name is given.
        
        @param name: name to build the function of
        @type name: string or RE
        @returns: 
                    1. None if no name is given
                    2. a lambda function
        @rtype: function
        """
        
        if name != None:
            if isinstance(name, str):
                return lambda x: re.match(".*"+name+".*",x, re.I)
            else: # assume regular expression
                return lambda x: name.match(x)
        else:
            return lambda x: True

    def geneticize_list (self, list_of_packages, only_cpv = False):
        """Convertes a list of cpv's into L{backend.Package}s.
        
        @param list_of_packages: the list of packages
        @type list_of_packages: string[]
        @param only_cpv: do nothing - return the passed list
        @type only_cpv: boolean
        @returns: converted list
        @rtype: PortagePackage[]
        """
        
        if not only_cpv:
            return [self.new_package(x) for x in list_of_packages]
        elif not isinstance(list_of_packages, list):
            return list(list_of_packages)
        else:
            return list_of_packages

    def get_global_settings (self, key):
        return self.settings.global_settings[key]

    def find_best (self, list, only_cpv = False):
        if only_cpv:
            return portage.best(list)
        else:
            return self.new_package(portage.best(list))

    def find_best_match (self, search_key, masked = False, only_installed = False, only_cpv = False):
        t = []
        
        if not only_installed:
            pkgSet = self.SET_TREE
        else:
            pkgSet = self.SET_INSTALLED

        t = self.find_packages(search_key, pkgSet = pkgSet, masked = masked, with_version = True, only_cpv = True)
        
        if VERSION >= (2,1,5):
            t += [pkg.get_cpv() for pkg in self.find_packages(search_key, self.SET_INSTALLED) if not (pkg.is_testing(True) or pkg.is_masked())]
        elif not only_installed: # no need to run twice
            t += self.find_packages(search_key, self.SET_INSTALLED, only_cpv=True)

        if t:
            t = list(set(t))
            return self.find_best(t, only_cpv)

        return None

    def _get_set (self, pkgSet):
        pkgSet = pkgSet.lower()
        if pkgSet == "": pkgSet = self.SET_ALL

        return self.setmap[pkgSet]()

    def find_packages (self, key = "", pkgSet = SystemInterface.SET_ALL, masked = False, with_version = True, only_cpv = False):
        return self.geneticize_list(self._get_set(pkgSet).find(key, masked, with_version, only_cpv), only_cpv or not with_version)

    def list_categories (self, name = None):
        categories = self.settings.global_settings.categories
        return filter(self.find_lambda(name), categories)

    def split_cpv (self, cpv):
        cpv = portage.dep_getcpv(cpv)
        return portage.catpkgsplit(cpv)

    def sort_package_list(self, pkglist):
        pkglist.sort(PortagePackage.compare_version) # XXX: waaah ... direct package naming... =/
        return pkglist

    def reload_settings (self):
        self.settings.load()

    def get_new_packages (self, packages):
        """Gets a list of packages and returns the best choice for each in the portage tree.

        @param packages: the list of packages
        @type packages: string[]
        @returns: the list of packages
        @rtype: backend.Package[]
        """

        new_packages = []

        def append(crit, best, inst):
            if not best:
                return

            if not best.is_installed() and (best.is_masked() or best.is_testing(True)): # check to not update unnecessairily
                for i in inst:
                    if i.matches(crit):
                        debug("The installed %s matches %s. Discarding upgrade to masked version %s.", i.get_cpv(), crit, best.get_version())
                        return
            
            new_packages.append(best)

        for p in packages:
            inst = self.find_packages(p, self.SET_INSTALLED)
            
            best_p = self.find_best_match(p)
            if best_p is None:
                best_p = self.find_best_match(p, masked = True)
                if best_p is None:
                    warning(_("No best match for %s. It seems not to be in the tree anymore.") % p)
                    continue
                else:
                    debug("Best match for %s is masked" % p)

            if len(inst) > 1:
                myslots = set()
                for i in inst: # get the slots of the installed packages
                    myslots.add(i.get_package_settings("SLOT"))

                myslots.add(best_p.get_package_settings("SLOT")) # add the slot of the best package in portage
                for slot in myslots:
                    crit = "%s:%s" % (p, slot)
                    append(crit, self.find_best_match(crit), inst)
            else:
                append(p, best_p, inst)

        return new_packages

    def get_updated_packages (self):
        packages = self.get_new_packages(self.find_packages(pkgSet = self.SET_INSTALLED, with_version = False))
        packages = [x for x in packages if x is not None and not x.is_installed()]
        return packages

    def update_world (self, sets = ("world", "system"), newuse = False, deep = False):
        packages = set()
        map(packages.add, itt.chain(*[self.find_packages(pkgSet = s, with_version = False) for s in sets]))

        states = [(["RDEPEND", "PDEPEND"], True)]
        if self.with_bdeps():
            states.append((["DEPEND"], True))

        checked = []
        updating = []
        raw_checked = {}
        def check (p, add_not_installed = True, prev_appended = False):
            """Checks whether a package is updated or not."""
            
            if p.get_slot_cp() in checked:
                return
            else:
                if (not p.is_installed()) and (not add_not_installed):
                    # don't add these packages to checked as we may see them again
                    # - and then we might have add_not_installed being True
                    return
                else:
                    checked.append(p.get_slot_cp())

            appended = False
            tempDeep = False

            if not p.is_installed():
                oldList = self.find_packages(p.get_slot_cp(), self.SET_INSTALLED)
                if oldList:
                    old = oldList[0] # we should only have one package here - else it is a bug
                else:
                    oldList = self.sort_package_list(self.find_packages(p.get_cp(), self.SET_INSTALLED))
                    if not oldList:
                        info(_("Found a not installed dependency: %s.") % p.get_cpv())
                        oldList = [p]
                    
                    old = oldList[-1]
                
                updating.append((p, old))
                appended = True
                p = old

            if newuse and p.is_installed() and p.is_in_system(): # there is no use to check newuse for a package which is not existing in portage anymore :)

                new_iuse = set(p.get_iuse_flags(installed = False)) # IUSE in the ebuild
                old_iuse = set(p.get_iuse_flags(installed = True)) # IUSE in the vardb

                # add forced flags, as they might trigger a rebuild
                new_iuse_f = set(p.get_iuse_flags(installed = False, removeForced = False))
                old_iuse_f = set(p.get_iuse_flags(installed = True, removeForced = False))
                
                if new_iuse.symmetric_difference(old_iuse): # difference between IUSE (w/o forced)
                    tempDeep = True
                    if not appended:
                        updating.append((p,p))
                        appended = True
                
                else: # check for difference between the _set_ useflags (w/ forced)
                    if new_iuse_f.intersection(p.get_actual_use_flags()).symmetric_difference(old_iuse_f.intersection(p.get_installed_use_flags())):
                        tempDeep = True
                        if not appended:
                            updating.append((p,p))
                            appended = True

            if deep or tempDeep:
                if (appended or prev_appended) and len(states) < 2:
                    real_states = states + [("PDEPEND", True), ("DEPEND", False)]
                else:
                    real_states = states
                for state in real_states:
                    for i in p.get_matched_dep_packages(state[0]):
                        if i not in raw_checked or raw_checked[i] == False:
                            raw_checked.update({i : state[1]})
                            bm = self.get_new_packages([i])
                            if not bm:
                                warning(_("Bug? No best match could be found for '%(package)s'. Needed by: '%(cpv)s'."), {"package" : i, "cpv": p.get_cpv()})
                            else:
                                for pkg in bm:
                                    if not pkg: continue
                                    check(pkg, state[1], appended) # XXX: should be 'or'ed with prev_appended?

        for p in self.get_new_packages(packages):
            if not p: continue # if a masked package is installed we have "None" here
            check(p, True)
        
        return updating

    def get_use_desc (self, flag, package = None):
        # In the first run the dictionaries 'use_descs' and 'local_use_descs' are filled.
        
        # fill cache if needed
        if not self.use_descs and not self.local_use_descs:
            for dir in [self.settings.global_settings["PORTDIR"]] + self.settings.global_settings["PORTDIR_OVERLAY"].split():
                
                # read use.desc
                try:
                    f = open(os.path.join(dir, "profiles/use.desc"))
                    for line in f:
                        line = line.strip()
                        if line and line[0] != '#':
                            fields = [x.strip() for x in line.split(" - ",1)]
                            if len(fields) == 2:
                                self.use_descs[fields[0]] = fields[1]
                except IOError:
                    pass
                finally:
                    f.close()

                # read use.local.desc
                try:
                    f = open(os.path.join(dir, "profiles/use.local.desc"))
                    for line in f:
                        line = line.strip()
                        if line and line[0] != '#':
                            fields = [x.strip() for x in line.split(":",1)]
                            if len(fields) == 2:
                                subfields = [x.strip() for x in fields[1].split(" - ",1)]
                                if len(subfields) == 2:
                                    self.local_use_descs[fields[0]].update([subfields])
                except IOError:
                    pass
                finally:
                    f.close()
        
        # start
        desc = self.use_descs.get(flag, "")
        if package is not None:
            if package in self.local_use_descs:
                desc = self.local_use_descs[package].get(flag, desc)
        
        return desc
