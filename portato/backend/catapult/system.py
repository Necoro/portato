# -*- coding: utf-8 -*-
#
# File: portato/backend/catapult/system.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import re, os
from gettext import lgettext as _
from threading import Event
import dbus
import catapult

from .package import CatapultPackage
from ..system_interface import SystemInterface
from ...helper import debug, info, warning, unique_array

class CatapultSystem (SystemInterface):

	def __init__ (self):
		SystemInterface.__init__(self)
		
		self.bus = dbus.SessionBus()
		# get the system
		so = self.bus.get_object(catapult.get_dbus_address(catapult.DEFAULT), catapult.CATAPULT_SYSTEM_BUS, follow_name_owner_changes = True)
		self.proxy = dbus.Interface(so, catapult.CATAPULT_SYSTEM_IFACE)

	def get_version (self):
		admint = dbus.Interface(self.bus.get_object(catapult.get_dbus_address(catapult.DEFAULT), catapult.CATAPULT_BUS), catapult.CATAPULT_ADMIN_IFACE)
		return "Catapult: %s v. %s" % (self.proxy.bus_name.split(".")[-1], str(admint.version()))

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
		split = self.proxy.split_cpv(cpv)
		if all(split):
			return map(str, split)
		else:
			return None

	def cpv_matches (self, cpv, criterion):
		return CatapultPackage(cpv).matches(criterion)

	def find_best(self, list, only_cpv = False):
		if only_cpv:
			return str(self.proxy.find_best(list))
		else:
			return CatapultPackage(self.proxy.find_best(list))

	def find_best_match (self, search_key, masked = False, only_installed = False, only_cpv = False):
		p = self.proxy.find_best_match(search_key, masked, only_installed)

		if p :
			if not only_cpv:
				return CatapultPackage(p)
			else:
				return str(p)
		return None

	def _wrap_find(self, key, masked, set, withVersion, only_cpv):
		
		l = []
		try:
			l = self.proxy.find_packages(key, set, masked, withVersion)
		except dbus.DBusException, e:
			name, data = str(e).split("\n")[-2].split(": ")[1:]

			if name == catapult.CATAPULT_ERR_AMBIGUOUS_PACKAGE:
				debug("Ambigous packages: %s.", data)
				l = []
				for cp in data.split(","):
					l += self.proxy.find_packages(cp, set, masked, withVersion)
			else:
				raise

		return self.geneticize_list(l, not(withVersion) or only_cpv)

	def find_packages (self, search_key, masked = False, only_cpv = False):
		return self._wrap_find(search_key, masked, "all", True, only_cpv)

	def find_installed_packages (self, search_key, masked = False, only_cpv = False):
		return self._wrap_find(search_key, masked, "installed", True, only_cpv)

	def find_system_packages (self, only_cpv = False):
#		result = self.proxy.find_system_packages()
#		if only_cpv:
#			return result
#		else:
#			return tuple(map(self.geneticize_list, result))
		return (self._wrap_find(search_key, False, "system", True, only_cpv), [])

	def find_world_packages (self, only_cpv = False):
#		result = self.proxy.find_world_packages()
#		if only_cpv:
#			return result
#		else:
#			return tuple(map(self.geneticize_list, result))
		return (self._wrap_find(search_key, False, "world", True, only_cpv), [])

	def _wrap_find_all (self, key, masked, set, withVersion, only_cpv):
		if not key:
			key = ""
		else:
			key = "*%s*" % key

		l = self.proxy.find_packages("", set, masked, withVersion)

		if key:
			l = catapult.filter_list(key, l)
		
		return self.geneticize_list(l, not(withVersion) or only_cpv)

	def find_all_installed_packages (self, name = None, withVersion = True, only_cpv = False):
		return self._wrap_find_all(name, True, "installed", withVersion, only_cpv)

	def find_all_uninstalled_packages (self, name = None, only_cpv = False):
		return self._wrap_find_all(name, True, "uninstalled", True, only_cpv)

	def find_all_packages (self, name = None, withVersion = True, only_cpv = False):
		return self._wrap_find_all(name, True, "all", withVersion, only_cpv)

	def find_all_world_packages (self, name = None, only_cpv = False):
		return self._wrap_find_all(name, True, "world", withVersion, only_cpv)
	
	def find_all_system_packages (self, name = None, only_cpv = False):
		return self._wrap_find_all(name, True, "system", withVersion, only_cpv)

	def list_categories (self, name = None):
		cats = self.proxy.list_categories()
		if name:
			cats = catapult.filter_list("*%s*" % name, cats)
		
		return map(str, cats)

	def sort_package_list(self, pkglist):
		return self.geneticize_list(self.proxy.sort_package_list([x.get_cpv() for x in pkglist]))
		
	def reload_settings (self):
		return self.proxy.reload_settings()

	def update_world (self, newuse = False, deep = False):
		
		ret = []
		e = Event()
				
		def wait (list):
			ret.extend([(CatapultPackage(x), CatapultPackage(y)) for x,y in list])
			e.set()

		def error (ex):
			e.set()
			raise ex
		
		self.proxy.update_world(newuse, deep, {}, reply_handler = wait, error_handler = error, timeout = 300)
		e.wait()
		return ret
	#	return [(CatapultPackage(x), CatapultPackage(y)) for x,y in self.proxy.update_world(newuse, deep, {}, timeout = 300)]

	def get_updated_packages (self):
		ret = []
		e = Event()
				
		def wait (list):
			ret.extend([CatapultPackage(x) for x in list])
			e.set()

		def error (ex):
			e.set()
			raise ex
		
		self.proxy.get_updated_packages(reply_handler = wait, error_handler = error, timeout = 300)
		e.wait()
		return ret

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
		default_opts = self.get_global_settings("EMERGE_DEFAULT_OPTS")
		opts = dict(os.environ)

		if default_opts:
			opt_list = default_opts.split()
			changed = False

			for option in ["--ask", "-a", "--pretend", "-p"]:
				if option in opt_list:
					opt_list.remove(option)
					changed = True
			
			if changed:
				opts.update(EMERGE_DEFAULT_OPTS = " ".join(opt_list))
		
		opts.update(TERM = "xterm")

		return opts
