# -*- coding: utf-8 -*-
#
# File: portato/gui/utils.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

# some stuff needed
import re
import logging

# some backend things
from ..backend import flags, system, set_system
from ..helper import _, debug, info, set_log_level 
from ..constants import USE_CATAPULT

# parser
from ..config_parser import ConfigParser

class Config (ConfigParser):
	
	def __init__ (self, cfgFile):
		"""Constructor.

		@param cfgFile: path to config file
		@type cfgFile: string"""

		ConfigParser.__init__(self, cfgFile)
		
		# read config
		self.parse()

		# local configs
		self.local = {}

	def modify_flags_config (self):
		"""Sets the internal config of the L{flags}-module.
		@see: L{flags.set_config()}"""

		flagCfg = {
				"usefile": self.get("useFile"), 
				"usePerVersion" : self.get_boolean("usePerVersion"),
				"maskfile" : self.get("maskFile"),
				"maskPerVersion" : self.get_boolean("maskPerVersion"),
				"testingfile" : self.get("keywordFile"),
				"testingPerVersion" : self.get_boolean("keywordPerVersion")}
		flags.set_config(flagCfg)

	def modify_debug_config (self):
		if self.get_boolean("debug"):
			level = logging.DEBUG
		else:
			level = logging.INFO

		set_log_level(level)

	def modify_system_config (self):
		"""Sets the system config.
		@see: L{backend.set_system()}"""
		if not USE_CATAPULT:
			set_system(self.get("system"))

	def modify_external_configs (self):
		"""Convenience function setting all external configs."""
		self.modify_debug_config()
		self.modify_flags_config()
		self.modify_system_config()

	def set_local(self, cpv, name, val):
		"""Sets some local config.

		@param cpv: the cpv describing the package for which to set this option
		@type cpv: string (cpv)
		@param name: the option's name
		@type name: string
		@param val: the value to set
		@type val: any"""
		
		if not cpv in self.local:
			self.local[cpv] = {}

		self.local[cpv].update({name:val})

	def get_local(self, cpv, name):
		"""Returns something out of the local config.

		@param cpv: the cpv describing the package from which to get this option
		@type cpv: string (cpv)
		@param name: the option's name
		@type name: string
		@return: value stored for the cpv and name or None if not found
		@rtype: any"""

		if not cpv in self.local:
			return None
		if not name in self.local[cpv]:
			return None

		return self.local[cpv][name]

	def write(self):
		"""Writes to the config file and modify any external configs."""
		ConfigParser.write(self)
		self.modify_external_configs()

class Database (object):
	"""An internal database which holds a simple dictionary cat -> [package_list]."""

	ALL = _("ALL")

	def __init__ (self):
		"""Constructor."""
		self.__initialize()

	def __initialize (self):
		self._db = {self.ALL:[]}
		self.inst_cats = set([self.ALL])
		self._restrict = None

	def __sort_key (self, x):
		return x[1].lower()

	def populate (self, category = None):
		"""Populates the database.
		
		@param category: An optional category - so only packages of this category are inserted.
		@type category: string
		"""
		
		# get the lists
		packages = system.find_all_packages(name = category, withVersion = False)
		installed = system.find_all_installed_packages(name = category, withVersion = False)
		
		# cycle through packages
		for p in packages:
			cat, pkg = p.split("/")
			if not cat in self._db: self._db[cat] = []
			inst = p in installed
			t = (cat, pkg, inst)
			self._db[cat].append(t)
			self._db[self.ALL].append(t)

			if inst:
				self.inst_cats.add(cat)

		for key in self._db: # sort alphabetically
			self._db[key].sort(key = self.__sort_key)

	def get_cat (self, cat = None, byName = True):
		"""Returns the packages in the category.
		
		@param cat: category to return the packages from; if None it defaults to "ALL"
		@type cat: string
		@param byName: selects whether to return the list sorted by name or by installation
		@type byName: boolean
		@return: an iterator over a list of tuples: (category, name, is_installed) or []
		@rtype: (string, string, boolean)<iterator>
		"""
		
		if not cat:
			cat = self.ALL

		try:
			def get_pkgs():
				if byName:
					for pkg in self._db[cat]:
						yield pkg
				else:
					ninst = []
					for pkg in self._db[cat]:
						if pkg[2]:
							yield pkg
						else:
							ninst.append(pkg)

					for pkg in ninst:
						yield pkg

			if self.restrict:
				return (pkg for pkg in get_pkgs() if self.restrict.search(pkg[1]))#if pkg[1].find(self.restrict) != -1)
			else:
				return get_pkgs()

		except KeyError: # cat is in category list - but not in portage
			info(_("Catched KeyError => %s seems not to be an available category. Have you played with rsync-excludes?"), cat)

	def get_categories (self, installed = False):
		"""Returns all categories.
		
		@param installed: Only return these with at least one installed package.
		@type installed: boolean
		@returns: the list of categories
		@rtype: string<iterator>
		"""

		if not self.restrict:
			if installed:
				cats = self.inst_cats
			else:
				cats = self._db.iterkeys()

		else:
			if installed:
				cats = set((pkg[0] for pkg in self.get_cat(self.ALL) if pkg[2]))
			else:
				cats = set((pkg[0] for pkg in self.get_cat(self.ALL)))

			if len(cats)>1:
				cats.add(self.ALL)

		return (cat for cat in cats)

	def reload (self, cat = None):
		"""Reloads the given category.
		
		@param cat: category
		@type cat: string
		"""

		if cat:
			del self._db[cat]
			try:
				self.inst_cats.remove(cat)
			except KeyError: # not in inst_cats - can be ignored
				pass
			self.populate(cat+"/")
		else:
			self.__initialize()
			self.populate()

	def get_restrict (self):
		return self._restrict

	def set_restrict (self, restrict):
		if not restrict:
			self._restrict = None
		else:
			try:
				regex = re.compile(restrict, re.I)
			except re.error, e:
				info(_("Error while compiling search expression: '%s'."), str(e))
			else: # only set self._restrict if no error occurred
				self._restrict = regex

	restrict = property(get_restrict, set_restrict)
