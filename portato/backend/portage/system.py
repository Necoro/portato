# -*- coding: utf-8 -*-
#
# File: portato/backend/portage/system.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import re, os
import types
import portage

import package
from settings import PortageSettings
from portato.helper import debug, unique_array
from portato.backend.system_interface import SystemInterface

class PortageSystem (SystemInterface):
	"""This class provides access to the portage-system."""
	
	def __init__ (self):
		"""Constructor."""
		self.settings = PortageSettings()
		portage.WORLD_FILE = self.settings.settings["ROOT"]+portage.WORLD_FILE

	def new_package (self, cpv):
		return package.PortagePackage(cpv)

	def get_config_path (self):
		return portage.USER_CONFIG_PATH

	def get_world_file_path (self):
		return portage.WORLD_FILE

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

	def find_lambda (self, name):
		"""Returns the function needed by all the find_all_*-functions. Returns None if no name is given.
		
		@param name: name to build the function of
		@type name: string
		@returns: 
					1. None if no name is given
					2. a lambda function
		@rtype: function"""
		
		if name != None:
			return lambda x: re.match(".*"+name+".*",x)
		else:
			return lambda x: True

	def geneticize_list (self, list_of_packages):
		"""Convertes a list of cpv's into L{backend.Package}s.
		
		@param list_of_packages: the list of packages
		@type list_of_packages: list of gentoolkit.Packages
		@returns: converted list
		@rtype: PortagePackage[]"""
		
		return [package.PortagePackage(x) for x in list_of_packages]

	def get_global_settings (self, key):
		return self.settings.settings[key]

	def find_best (self, list):
		return package.PortagePackage(portage.best(list))

	def find_best_match (self, search_key, only_installed = False):
		t = None
		if not only_installed:
			t = self.settings.porttree.dep_bestmatch(search_key)
		else:
			t = self.settings.vartree.dep_bestmatch(search_key)
		if t:
			return package.PortagePackage(t)
		return None

	def find_packages (self, search_key, masked=False):
		try:
			if masked:
				t = self.settings.porttree.dbapi.xmatch("match-all", search_key)
				t += self.settings.vartree.dbapi.match(search_key)
			else:
				t = self.settings.porttree.dbapi.match(search_key)
				t += self.settings.vartree.dbapi.match(search_key)
		# catch the "ambigous package" Exception
		except ValueError, e:
			if type(e[0]) == types.ListType:
				t = []
				for cp in e[0]:
					if masked:
						t += self.settings.porttree.dbapi.xmatch("match-all", cp)
						t += self.settings.vartree.dbapi.match(cp)
					else:
						t += self.settings.porttree.dbapi.match(cp)
						t += self.settings.vartree.dbapi.match(cp)
			else:
				raise ValueError(e)
		# Make the list of packages unique
		t = unique_array(t)
		t.sort()
		return self.geneticize_list(t)

	def find_installed_packages (self, search_key, masked = False):
		try:
			t = self.settings.vartree.dbapi.match(search_key)
		# catch the "ambigous package" Exception
		except ValueError, e:
			if type(e[0]) == types.ListType:
				t = []
				for cp in e[0]:
					t += self.settings.vartree.dbapi.match(cp)
			else:
				raise ValueError(e)

		return self.geneticize_list(t)

	def __find_resolved_unresolved (self, list, check):
		"""Checks a given list and divides it into a "resolved" and an "unresolved" part.

		@param list: list of cpv's
		@type list: string[]
		@param check: function called to check whether an entry is ok
		@type check: function(cpv)

		@returns: the divided list: (resolved, unresolved)
		@rtype: (Package[], Package[])"""
		resolved = []
		unresolved = []
		for x in list:
			cpv = x.strip()
			if len(cpv) and check(cpv):
				pkg = self.find_best_match(cpv)
				if pkg:
					resolved.append(pkg)
				else:
					unresolved.append(cpv)
		return (resolved, self.geneticize_list(unresolved))
	
	def find_system_packages (self):
		pkglist = self.settings.settings.packages

		return self.__find_resolved_unresolved(pkglist, lambda cpv: cpv[0] == "*")

	def find_world_packages (self):
		f = open(portage.WORLD_FILE)
		pkglist = f.readlines()
		f.close()

		return self.__find_resolved_unresolved(pkglist, lambda cpv: cpv[0] != "#")

	def find_all_installed_packages (self, name = None, withVersion=True):
		if withVersion:
			t = self.settings.vartree.dbapi.cpv_all()
			if name:
				t = filter(self.find_lambda(name),t)
			return self.geneticize_list(t)
		
		else:
			t = self.settings.vartree.dbapi.cp_all()
			if name:
				t = filter(self.find_lambda(name),t)
			return t

	def find_all_uninstalled_packages (self, name = None):
		alist = self.find_all_packages(name)
		return self.geneticize_list([x for x in alist if not x.is_installed()])	

	def find_all_packages (self, name = None, withVersion = True):
		t = self.settings.porttree.dbapi.cp_all()
		t += self.settings.vartree.dbapi.cp_all()
		if name:
			t = filter(self.find_lambda(name),t)
		t = unique_array(t)
		
		if (withVersion):
			t2 = []
			for x in t:
				t2 += self.settings.porttree.dbapi.cp_list(x)
				t2 += self.settings.vartree.dbapi.cp_list(x)
				t2 = unique_array(t2)
			return self.geneticize_list(t2)
		else:
			return t;

	def find_all_world_packages (self, name = None):
		world = filter(self.find_lambda(name), [x.get_cpv() for x in self.find_world_packages()[0]])
		world = unique_array(world)
		return self.geneticize_list(world)

	def find_all_system_packages (self, name = None):
		sys = filter(self.find_lambda(name), [x.get_cpv() for x in self.find_system_packages()[0]])
		sys = unique_array(sys)
		return self.geneticize_list(sys)

	def list_categories (self, name = None):
		categories = self.settings.settings.categories
		return filter(self.find_lambda(name), categories)

	def split_cpv (self, cpv):
		cpv = portage.dep_getcpv(cpv)
		return portage.catpkgsplit(cpv)

	def sort_package_list(self, pkglist):
		pkglist.sort(package.PortagePackage.compare_version)
		return pkglist

	def reload_settings (self):
		self.settings.load()

	def update_world (self, newuse = False, deep = False):
		# read world file
		world = open(portage.WORLD_FILE)
		packages = []
		for line in world:
			line = line.strip()
			if len(line) == 0: continue # empty line
			if line[0] == "#": continue # comment
			packages.append(line)
		world.close()

		# append system packages
		packages.extend(unique_array([p.get_cp() for p in self.find_all_system_packages()]))

		def get_new_packages (packages):
			new_packages = []
			for p in packages:
				inst = self.find_installed_packages(p)
				if len(inst) > 1:
					myslots = set()
					for i in inst: # get the slots of the installed packages
						myslots.add(i.get_package_settings("SLOT"))

					myslots.add(self.find_best_match(p).get_package_settings("SLOT")) # add the slot of the best package in portage
					for slot in myslots:
						new_packages.append(\
								self.find_best(\
								[x.get_cpv() for x in self.find_packages("%s:%s" % (i.get_cp(), slot))]\
								))
				else:
					new_packages.append(self.find_best_match(p))

			return new_packages
							
		checked = []
		updating = []
		raw_checked = []
		def check (p, add_not_installed = True):
			"""Checks whether a package is updated or not."""
			if p.get_cp() in checked: return
			else: checked.append(p.get_cp())

			appended = False
			tempDeep = False

			if not p.is_installed():
				oldList = self.find_installed_packages(p.get_slot_cp())
				if oldList: 
					old = oldList[0] # we should only have one package here - else it is a bug
				else:
					oldList = self.sort_package_list(self.find_installed_packages(p.get_cp()))
					if not oldList:
						if add_not_installed:
							debug("Not found installed",p.get_cpv(),"==> adding")
							oldList = [p]
						else:
							return
					old = oldList[-1]
				
				updating.append((p, old))
				appended = True
				p = old

			if newuse and p.is_installed() and p.is_in_system(): # there is no use to check newuse for a package which is not existing in portage anymore :)

				new_iuse = set(p.get_all_use_flags(installed = False)) # IUSE in the ebuild
				old_iuse = set(p.get_all_use_flags(installed = True)) # IUSE in the vardb
				
				if new_iuse.symmetric_difference(old_iuse): # difference between new_iuse and old_iuse
					tempDeep = True
					if not appended:
						updating.append((p,p))
						appended = True
				
				else:
					old = set(p.get_installed_use_flags())
					new = set(p.get_global_settings("USE").split())
					
					if new_iuse.intersection(new) != old_iuse.intersection(old):
						tempDeep = True
						if not appended:
							updating.append((p,p))
							appended = True

			if deep or tempDeep:
				states = [(["RDEPEND","PDEPEND"],True), (["DEPEND"], False)]
				
				for state in states:
					for i in p.get_matched_dep_packages(state[0]):
						if i not in raw_checked:
							raw_checked.append(i)
							bm = get_new_packages([i])
							if not bm: 
								debug("Bug? No best match could be found:",i)
							else:
								for pkg in bm: 
									if not pkg: continue
									check(pkg, state[1])

		for p in get_new_packages(packages):
			if not p: continue # if a masked package is installed we have "None" here
			check(p, True)
		
		return updating
		
	use_descs = {}
	local_use_descs = {}
	def get_use_desc (self, flag, package = None):
		# In the first run the dictionaries 'use_descs' and 'local_use_descs' are filled.
		
		# fill cache if needed
		if self.use_descs == {} or self.local_use_descs == {}:
			# read use.desc
			fd = open(self.settings.settings["PORTDIR"]+"/profiles/use.desc")
			lines = fd.readlines()
			fd.close()
			for line in lines:
				line = line.strip()
				if line != "" and line[0] != '#':
					fields = [x.strip() for x in line.split(" - ",1)]
					if len(fields) == 2:
						self.use_descs[fields[0]] = fields[1]

			# read use.local.desc
			fd = open(self.settings.settings["PORTDIR"]+"/profiles/use.local.desc")
			lines = fd.readlines()
			fd.close()
			for line in lines:
				line = line.strip()
				if line != "" and line[0] != '#':
					fields = [x.strip() for x in line.split(":",1)]
					if len(fields) == 2:
						if not fields[0] in self.local_use_descs: # create
							self.local_use_descs[fields[0]] = {}
						subfields = [x.strip() for x in fields[1].split(" - ",1)]
						if len(subfields) == 2:
							self.local_use_descs[fields[0]][subfields[0]] = subfields[1]
		
		# start
		desc = None
		if flag in self.use_descs:
			desc = self.use_descs[flag]
		if package != None:
			if package in self.local_use_descs:
				if flag in self.local_use_descs[package]:
					desc = self.local_use_descs[package][flag]
		return desc
