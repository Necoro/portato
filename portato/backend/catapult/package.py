# -*- coding: utf-8 -*-
#
# File: portato/backend/catapult/package.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

from ..package import Package
from .. import flags
from .. import system
from ..exceptions import BlockedException, PackageNotFoundException
from ...helper import debug, unique_array

import dbus
import catapult

import os.path
from gettext import lgettext as _

class CatapultPackage(Package):

	bus = dbus.SessionBus()
	dbus_object = bus.get_object(catapult.get_dbus_address(catapult.DEFAULT), catapult.CATAPULT_PACKAGE_BUS, follow_name_owner_changes = True)
	proxy = dbus.Interface(dbus_object, catapult.CATAPULT_PACKAGE_IFACE)
	
	def _new_flags (self):
		flags = self.get_new_use_flags()

		nflags = []

		for flag in flags:
			if flag[0] == "~":
				nflags.append(flag[1:], True)
			else:
				nflags.append(flag, False)

		return nflags
	
	def use_expanded (self, flag, suggest = None):
		if not suggest:
			suggest = ""
		s = str(self.proxy.use_expanded(self.get_cpv(), flag, suggest))
		if s:
			return s
		else:
			return None

	def get_package_path(self):
		return str(self.proxy.get_package_path(self.get_cpv()))

	def is_installed(self):
		return self.proxy.is_installed(self.get_cpv())

	def is_overlay(self):
		return self.proxy.is_in_overlay(self.get_cpv())

	def get_overlay_path(self):
		return str(self.proxy.get_overlay_path(self.get_cpv()))
		
	def is_in_system (self):
		return self.proxy.is_in_system(self.get_cpv())

	def is_missing_keyword(self):
		return self.proxy.is_missing_keyword(self.get_cpv())
		
	def is_testing(self, use_keywords = False):
		if not use_keywords:
			return self.proxy.is_testing(self.get_cpv(), False)
		else:
			status = flags.new_testing_status(self.get_cpv())
			if status is None:
				return self.proxy.is_testing(self.get_cpv(), True)
			else:
				return status

	def is_masked (self, use_changed = True):
		if use_changed:
			status = flags.new_masking_status(self.get_cpv())
			if status != None: # we have locally changed it
				if status == "masked": return True
				elif status == "unmasked": return False
				else:
					error(_("BUG in flags.new_masking_status. It returns \'%s\'"), status)
			else: # we have not touched the status
				return self.proxy.is_masked(self.get_cpv())
		else: # we want the original portage value XXX: bug if masked by user AND by system
			if self.proxy.is_masked(self.get_cpv()):
				if not flags.is_locally_masked(self, changes = False): # assume that if it is locally masked, it is not masked by the system
					return True

			return False

	def get_masking_reason (self):
		return str(self.proxy.get_masking_reason(self.get_cpv()))
		
	def get_iuse_flags (self, installed = False, removeForced = True):
		return [str(x) for x in self.proxy.get_iuse_flags(self.get_cpv(), installed, removeForced)]

	def get_matched_dep_packages (self, depvar):
		return [str(x) for x in self.proxy.get_matched_dep_packages(self.get_cpv(), self._new_flags())]
		
	def get_dep_packages (self, depvar = ["RDEPEND", "PDEPEND", "DEPEND"], with_criterions = False):
		pkgs = self.proxy.get_dep_packages(self.get_cpv(), depvar, self.get_new_use_flags())

		if not with_criterions:
			return [str(x) for x,y in pkgs]
		else:
			return [(str(x),str(y)) for x,y in pkgs]

	def get_global_settings(self, key, installed = True):
		return str(self.proxy.get_global_settings(self.get_cpv(), key, installed))

	def get_ebuild_path(self):
		return str(self.proxy.get_ebuild_path(self.get_cpv()))

	def get_package_settings(self, var, tree = True):
		return str(self.proxy.get_package_settings(self.get_cpv(), var, tree))

	def get_installed_use_flags(self):
		return self.proxy.get_installed_use_flags(self.get_cpv())

	def get_actual_use_flags(self):
		return self.proxy.get_actual_use_flags(self.get_cpv(), self._new_flags())

	def compare_version(self, other):
		return self.proxy.compare_version(self.get_cpv(), other.get_cpv())

	def matches (self, criterion):
		return self.proxy.matches(self.get_cpv(), criterion)

	def get_files (self):
		return self.proxy.get_files(self.get_cpv())

	def get_dependencies (self):
		from ...dependency import DependencyTree
		d = DependencyTree()
		d.add("Dependency calculation not supported for Catapult Backend")
		return d

	def get_name(self):
		return str(self.proxy.get_name(self.get_cpv()))

	def get_version(self):
		return str(self.proxy.get_version(self.get_cpv()))

	def get_category(self):
		return str(self.proxy.get_category(self.get_cpv()))

