# -*- coding: utf-8 -*-
#
# File: portato/backend/catapult/package.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
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

import os.path
from gettext import lgettext as _

class CatapultPackage(Package):

	def __init__ (self, cpv):
		Package.__init__(self, cpv)

		self.bus = dbus.SessionBus()
		# get the system
		po = self.bus.get_object("org.gentoo.catapult.portage", "/org/gentoo/catapult/Package")
		self.proxy = dbus.Interface(po, "org.gentoo.catapult.Package")

	def use_expanded (self, flag, suggest = None):
		if not suggest:
			suggest = ""
		return self.proxy.use_expanded(self.get_cpv(), flag, suggest)

	def get_cp (self):
		return self.proxy.get_cp(self.get_cpv())

	def get_slot_cp (self):
		return self.proxy.get_slot_cp(self.get_cpv())

	def get_package_path(self):
		return self.proxy.get_package_path(self.get_cpv())

	def is_installed(self):
		return self.proxy.is_installed(self.get_cpv())

	def is_overlay(self):
		return self.proxy.is_overlay(self.get_cpv())

	def get_overlay_path(self):
		return self.proxy.is_overlay_path(self.get_cpv())
		
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
#			else: # more difficult: get the ones we unmasked, but are masked by the system
#				try:
#					masked = self._settings.settings.pmaskdict[self.get_cp()]
#				except KeyError: # key error: not masked
#					return False
#
#				for cpv in masked:
#					if self.matches(cpv):
#						if not flags.is_locally_masked(self, changes = False): # assume that if it is locally masked, it is not masked by the system
#							return True
#						else:
#							return False

			return False

	def get_masking_reason (self):
		return self.proxy.get_masking_reason(self.get_cpv())
		
	def get_iuse_flags (self, installed = False):
		return self.proxy.get_iuse_flags(self.get_cpv(), installed)

	def get_matched_dep_packages (self, depvar):
		return self.proxy.get_matched_dep_packages(self.get_cpv(), self.get_new_use_flags())
		
	def get_dep_packages (self, depvar = ["RDEPEND", "PDEPEND", "DEPEND"], with_criterions = False):
		return self.proxy.get_dep_packages(self.get_cpv(), depvar, self.get_new_use_flags(), with_criterions)

	def get_global_settings(self, key):
		return self.proxy.get_global_settings(self.get_cpv(), key)

	def get_ebuild_path(self):
		return self.proxy.get_ebuild_path(self.get_cpv())

	def get_package_settings(self, var, tree = True):
		return self.proxy.get_package_settings(self.get_cpv(), var, tree)

	def get_use_flags(self):
		return " ".join(self.proxy.get_use_flags(self.get_cpv()))

	def compare_version(self, other):
		return self.proxy.compare_version(self.get_cpv(), other)

	def matches (self, criterion):
		return self.proxy.matches(self.get_cpv(), criterion)
