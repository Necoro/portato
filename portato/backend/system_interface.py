# -*- coding: utf-8 -*-
#
# File: portato/backend/system_interface.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

class SystemInterface (object):
    
    SET_ALL = "__portato_all__"
    SET_TREE = "__portato_tree__"
    SET_INSTALLED = "__portato_installed__"
    SET_UNINSTALLED = "__portato_uninstalled__"

    def eapi_supported (self, eapi):
        """Signals, whether the given eapi is supported.

        @rtype: boolean"""
        raise NotImplementedError

    def has_set_support (self):
        """Signals, whether this backend supports sets.

        @rtype: boolean
        """
        raise NotImplementedError

    def get_sets (self):
        """Returns all supported sets in tuples consisting of name and description.
        If sets aren't supported, at least "world" and "system" have to be returned.

        @rtype: iter(string, string)
        """
        raise NotImplementedError

    def get_version (self):
        """Returns the version of the used backend.

        @rtype: string
        """
        raise NotImplementedError

    def split_cpv (self, cpv):
        """Splits a cpv into all its parts.

        @param cpv: the cpv to split
        @type cpv: string
        @returns: the splitted cpv
        @rtype: string[]
        """

        raise NotImplementedError

    def cpv_matches (self, cpv, criterion):
        """Checks whether a cpv matches a specific criterion.

        @param cpv: cpv to check
        @type cpv: string
        @param criterion: criterion to check against
        @type criterion: string
        @returns: match result
        @rtype: boolean
        """

        raise NotImplementedError
    
    def find_best(self, list, only_cpv = False):
        """Returns the best package out of a list of packages.

        @param list: the list of packages to select from
        @type list: string[]
        @param only_cpv: do not return package but only the cpv
        @type only_cpv: boolean

        @returns: the best package
        @rtype: backend.Package or string
        """
        
        raise NotImplementedError

    def find_best_match (self, search_key, masked = False, only_installed = False, only_cpv = False):
        """Finds the best match in the portage tree. It does not find masked packages!
        
        @param search_key: the key to find in the portage tree
        @type search_key: string
        @param masked: if True, also look for masked packages
        @type masked: boolean
        @param only_installed: if True, only installed packages are searched
        @type only_installed: boolean
        @param only_cpv: do not return package but only the cpv
        @type only_cpv: boolean
        
        @returns: the package found or None
        @rtype: backend.Package or string
        """

        raise NotImplementedError

    def find_packages (self, key, pkgSet = SET_ALL, masked = False, with_version = True, only_cpv = False):
        """This returns a list of packages matching the key.
        As key, it is allowed to use basic regexps (".*") and the normal package specs. But not a combination
        of them.
        
        @param key: the key to look for
        @type key: string
        @param all: the package set to use
        @type all: string
        @param masked: if True, also look for masked packages
        @type masked: boolean
        @param with_version: if True, return CPVs - else CP
        @type with_version: boolean
        @param only_cpv: do not return package but only the cpv. if with_version is False, this is ignored
        @type only_cpv: boolean
        
        @returns: list of found packages
        @rtype: backend.Package[] or string[]
        """

        raise NotImplementedError

    def list_categories (self, name = None):
        """Finds all categories matching a name or all if no name is specified.

        @param name: the name to look for - it is expanded to .*name.* ; if None, all categories are returned
        @type name: string or None
        @returns: all categories found
        @rtype: string[]
        """

        raise NotImplementedError

    def sort_package_list(self, pkglist):
        """Sorts a package list in the same manner portage does.
        
        @param pkglist: list to sort
        @type pkglist: Packages[]
        """

        raise NotImplementedError
        
    def reload_settings (self):
        """Reloads portage."""

        raise NotImplementedError

    def update_world (self, newuse = False, deep = False):
        """Calculates the packages to get updated in an update world.

        @param newuse: Checks if a use-flag has a different state then to install time.
        @type newuse: boolean
        @param deep: Not only check world packages but also there dependencies.
        @type deep: boolean
        @returns: a list of the tuple (new_package, old_package)
        @rtype: (backend.Package, backend.Package)[]
        """

        raise NotImplementedError

    def get_updated_packages (self):
        """Returns the packages for which a newer package is available in the portage tree and installable (thus not masked).
        This differs from update_world as it takes all installed packages into account but ignores changed useflags.

        @returns: the list of new packages
        @rtype: backend.Package[]
        """

        raise NotImplementedError

    def get_use_desc (self, flag, package = None):
        """Returns the description of a specific useflag or None if no desc was found. 
        If a package is given (in the <cat>/<name> format) the local use descriptions are searched too.
        
        @param flag: flag to get the description for
        @type flag: string
        @param package: name of a package: if given local use descriptions are searched too
        @type package: cp-string
        @returns: found description
        @rtype: string
        """

        raise NotImplementedError

    def get_global_settings(self, key):
        """Returns the value of a global setting, i.e. ARCH, USE, ROOT, DISTDIR etc.
        
        @param key: the setting to return
        @type key: string
        @returns: the value of this setting
        @rtype: string
        """

        raise NotImplementedError

    def new_package (self, cpv):
        """Returns an instance of the appropriate Package-Subclass.

        @param cpv: the cpv to create the package from
        @type cpv: string
        @returns: a new Package-object.
        @rtype: Package
        """

        raise NotImplementedError

    def get_config_path (self):
        """Returns the actual path to the config files.
        
        @returns: the path, e.g. /etc/portage
        @rtype: string
        """

        raise NotImplementedError

    def get_sync_command (self):
        """Returns the command(s) to run for syncing. This can be overridden by the user.

        @returns: command to run
        @rtype: string[]
        """

        raise NotImplementedError

    def get_merge_command (self):
        """Returns the command(s) to run for the merging.

        @returns: command to run
        @rtype: string[]
        """

        raise NotImplementedError

    def get_oneshot_option (self):
        """Returns the options to append for marking a merge as "oneshot".

        @returns: option(s) to append
        @rtype: string[]
        """

        raise NotImplementedError

    def get_newuse_option (self):
        """Returns the options to append for marking a merge as "newuse".

        @returns: option(s) to append
        @rtype: string[]
        """

        raise NotImplementedError

    def get_deep_option (self):
        """Returns the options to append for marking a merge as "deep".

        @returns: option(s) to append
        @rtype: string[]
        """

        raise NotImplementedError

    def get_update_option (self):
        """Returns the options to append for marking a merge as "update".

        @returns: option(s) to append
        @rtype: string[]
        """

        raise NotImplementedError

    def get_pretend_option (self):
        """Returns the options to append for marking a merge as "pretend".

        @returns: option(s) to append
        @rtype: string[]
        """

        raise NotImplementedError

    def get_unmerge_option (self):
        """Returns the options to append for marking a merge as "unmerge".

        @returns: option(s) to append
        @rtype: string[]
        """

        raise NotImplementedError

    def get_environment (self):
        """Returns a dictionary of environment variables to set prior to do an emerge.

        @returns: environment variables
        @rtype: dict{string : string}
        """

        raise NotImplementedError
