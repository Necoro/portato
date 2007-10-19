# -*- coding: utf-8 -*-
#
# File: portato/backend/catapult/system.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import re, os
from gettext import lgettext as _
import dbus

from .package import CatapultPackage
from ..system_interface import SystemInterface
from ...helper import debug, info, warning, unique_array

class CatapultSystem (SystemInterface):

	def __init__ (self):
		SystemInterface.__init__(self)
		
		self.bus = dbus.SessionBus()
		# get the system
		so = self.bus.get_object("org.gentoo.catapult.portage", "/org/gentoo/catapult/System")
		self.proxy = dbus.Interface(so, "org.gentoo.catapult.System")

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
			return [CatapultPackage(x) for x in list_of_packages]
		else:
			return [str(x) for x in list_of_packages]


	def split_cpv (self, cpv):
		return [str(x) for x in self.proxy.split_cpv(cpv)]

	def cpv_matches (self, cpv, criterion):
		return CatapultPackage(cpv).matches(criterion)

	def find_best(self, list, only_cpv = False):
		if only_cpv:
			return str(self.proxy.find_best(list))
		else:
			return CatapultPackage(self.proxy.find_best(list))

	def find_best_match (self, search_key, masked = False, only_installed = False, only_cpv = False):
		p = self.proxy.find_best_match(search_key, masked, only_installed)

		if p and not only_cpv:
			return CatapultPackage(p)
		return str(p)

	def find_packages (self, search_key, masked = False, only_cpv = False):
		return self.geneticize_list(self.proxy.find_packages(search_key, masked), only_cpv)

	def find_installed_packages (self, search_key, masked = False, only_cpv = False):
		return self.geneticize_list(self.proxy.find_installed_packages(search_key, masked), only_cpv)

	def find_system_packages (self, only_cpv = False):
			
		result = self.proxy.find_system_packages()
		if only_cpv:
			return result
		else:
			return tuple(map(self.geneticize_list, result))

	def find_world_packages (self, only_cpv = False):
		result = self.proxy.find_world_packages()
		if only_cpv:
			return result
		else:
			return tuple(map(self.geneticize_list, result))

	def find_all_installed_packages (self, name = None, withVersion = True, only_cpv = False):
		if not name:
			name = ""
		return self.geneticize_list(self.proxy.find_all_installed_packages(name, withVersion), (not withVersion) or only_cpv)

	def find_all_uninstalled_packages (self, name = None, only_cpv = False):
		if not name:
			name = ""
		return self.geneticize_list(self.proxy.find_all_uninstalled_packages(name), only_cpv)

	def find_all_packages (self, name = None, withVersion = True, only_cpv = False):
		if not name:
			name = ""
		return self.geneticize_list(self.proxy.find_all_packages(name, withVersion), (not withVersion) or only_cpv)

	def find_all_world_packages (self, name = None, only_cpv = False):
		if not name:
			name = ""
		return self.geneticize_list(self.proxy.find_all_world_packages(name), only_cpv)
	
	def find_all_system_packages (self, name = None, only_cpv = False):
		if not name:
			name = ""
		return self.geneticize_list(self.proxy.find_all_system_packages(name), only_cpv)

	def list_categories (self, name = None):
		if not name:
			name = ""
		return [str(x) for x in self.proxy.list_categories(name)]

	def sort_package_list(self, pkglist):
		return self.geneticize_list(self.proxy.sort_package_list([x.get_cpv() for x in pkglist]))
		
	def reload_settings (self):
		return self.proxy.reload_settings()

	def update_world (self, newuse = False, deep = False):
		return [(CatapultPackage(x), CatapultPackage(y)) for x,y in self.proxy.update_world(newuse, deep, {})]

	def get_updated_packages (self):
		return self.geneticize_list(self.proxy.get_updated_packages())

	def get_use_desc (self, flag, package = None):
		if not package:
			package = ""
		return str(self.proxy.get_use_desc(flag, package))

	def get_global_settings(self, key):
		return str(self.proxy.get_global_settings(key))

	def new_package (self, cpv):
		return CatapultPackage(cpv)

	def get_config_path (self):
		return str(self.proxy.get_config_path())

	def get_world_file_path (self):
		return str(self.proxy.get_world_file_path())
	
	def get_sync_command (self):
		return [str(x) for x in self.proxy.get_sync_command()]

	def get_merge_command (self):
		return [str(x) for x in self.proxy.get_merge_command()]

	def get_oneshot_option (self):
		return [str(x) for x in self.proxy.get_oneshot_option()]

	def get_newuse_option (self):
		return [str(x) for x in self.proxy.get_newuse_option()]

	def get_deep_option (self):
		return [str(x) for x in self.proxy.get_deep_option()]

	def get_update_option (self):
		return [str(x) for x in self.proxy.get_update_option()]

	def get_pretend_option (self):
		return [str(x) for x in self.proxy.get_pretend_option()]

	def get_unmerge_option (self):
		return [str(x) for x in self.proxy.get_unmerge_option()]

	def get_environment (self):
		return self.proxy.get_environment()
