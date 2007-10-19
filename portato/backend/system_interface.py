# -*- coding: utf-8 -*-
#
# File: portato/backend/system_interface.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

class SystemInterface (object):

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

	def find_packages (self, search_key, masked = False, only_cpv = False):
		"""This returns a list of packages which have to fit exactly. Additionally ranges like '<,>,=,~,!' et. al. are possible.
		
		@param search_key: the key to look for
		@type search_key: string
		@param masked: if True, also look for masked packages
		@type masked: boolean
		@param only_cpv: do not return package but only the cpv
		@type only_cpv: boolean
		
		@returns: list of found packages
		@rtype: backend.Package[] or string[]
		"""

		raise NotImplementedError


	def find_installed_packages (self, search_key, masked = False, only_cpv = False):
		"""This returns a list of packages which have to fit exactly. Additionally ranges like '<,>,=,~,!' et. al. are possible.
		
		@param search_key: the key to look for
		@type search_key: string
		@param masked: if True, also look for masked packages
		@type masked: boolean
		@param only_cpv: do not return package but only the cpv
		@type only_cpv: boolean
		
		@returns: list of found packages
		@rtype: backend.Package[] or string[]
		"""

		raise NotImplementedError

	def find_system_packages (self, only_cpv = False):
		"""Looks for all packages saved as "system-packages".
		
		@param only_cpv: do not return package but only the cpv
		@type only_cpv: boolean

		@returns: a tuple of (resolved_packages, unresolved_packages).
		@rtype: (backend.Package[], backend.Package[]) or (string[], string[])
		"""

		raise NotImplementedError

	def find_world_packages (self, only_cpv = False):
		"""Looks for all packages saved in the world-file.
		
		@param only_cpv: do not return package but only the cpv
		@type only_cpv: boolean

		@returns: a tuple of (resolved_packages, unresolved_packages).
		@rtype: (backend.Package[], backend.Package[]) or (string[], string[])
		"""

		raise NotImplementedError

	def find_all_installed_packages (self, name = None, withVersion = True, only_cpv = False):
		"""Finds all installed packages matching a name or all if no name is specified.

		@param name: the name to look for - it is expanded to .*name.* ; if None, all packages are returned
		@type name: string or None
		@param withVersion: if True version-specific packages are returned; else only the cat/package-strings a delivered
		@type withVersion: boolean
		@param only_cpv: do not return package but only the cpv
		@type only_cpv: boolean

		@returns: all packages/cp-strings found
		@rtype: backend.Package[] or string[]
		"""

		raise NotImplementedError

	def find_all_uninstalled_packages (self, name = None, only_cpv = False):
		"""Finds all uninstalled packages matching a name or all if no name is specified.

		@param name: the name to look for - it is expanded to .*name.* ; if None, all packages are returned
		@type name: string or None
		@param only_cpv: do not return package but only the cpv
		@type only_cpv: boolean

		@returns: all packages found
		@rtype: backend.Package[] or string[]
		"""

		raise NotImplementedError

	def find_all_packages (self, name = None, withVersion = True, only_cpv = False):
		"""Finds all packages matching a name or all if no name is specified.

		@param name: the name to look for - it is expanded to .*name.* ; if None, all packages are returned
		@type name: string or None
		@param withVersion: if True version-specific packages are returned; else only the cat/package-strings a delivered
		@type withVersion: boolean
		@param only_cpv: do not return package but only the cpv
		@type only_cpv: boolean

		@returns: all packages/cp-strings found
		@rtype: backend.Package[] or string[]
		"""

		raise NotImplementedError
		
	def find_all_world_packages (self, name = None, only_cpv = False):
		"""Finds all world packages matching a name or all if no name is specified.

		@param name: the name to look for - it is expanded to .*name.* ; if None, all packages are returned
		@type name: string or None
		@param only_cpv: do not return package but only the cpv
		@type only_cpv: boolean

		@returns: all packages found
		@rtype: backend.Package[] or string[]
		"""

		raise NotImplementedError

	def find_all_system_packages (self, name = None, only_cpv = False):
		"""Finds all system packages matching a name or all if no name is specified.

		@param name: the name to look for - it is expanded to .*name.* ; if None, all packages are returned
		@type name: string or None
		@param only_cpv: do not return package but only the cpv
		@type only_cpv: boolean

		@returns: all packages found
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

	def get_world_file_path (self):
		"""Returns the path to the world file.

		@returns: the path of the world file
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
