# -*- coding: utf-8 -*-
#
# File: portato/backend/portage_helper.py
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

from portage_util import unique_array

from portato.backend import portage_settings
import package

from portato.helper import debug

def find_lambda (name):
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

def geneticize_list (list_of_packages):
	"""Convertes a list of cpv's into L{backend.Package}s.
	
	@param list_of_packages: the list of packages
	@type list_of_packages: list of gentoolkit.Packages
	@returns: converted list
	@rtype: backend.Package[]"""
	
	return [package.Package(x) for x in list_of_packages]

def find_best (list):
	"""Returns the best package out of a list of packages.

	@param list: the list of packages to select from
	@type list: string[]
	@returns: the best package
	@rtype: backend.Package"""
	
	return package.Package(portage.best(list))

def find_best_match (search_key, only_installed = False):
	"""Finds the best match in the portage tree. It does not find masked packages!
	
	@param search_key: the key to find in the portage tree
	@type search_key: string
	@param only_installed: if True, only installed packages are searched
	@type only_installed: boolean
	
	@returns: the package found or None
	@rtype: backend.Package"""

	t = None
	if not only_installed:
		t = portage_settings.porttree.dep_bestmatch(search_key)
	else:
		t = portage_settings.vartree.dep_bestmatch(search_key)
	if t:
		return package.Package(t)
	return None

def find_packages (search_key, masked=False):
	"""This returns a list of packages which have to fit exactly. Additionally ranges like '<,>,=,~,!' et. al. are possible.
	
	@param search_key: the key to look for
	@type search_key: string
	@param masked: if True, also look for masked packages
	@type masked: boolean
	
	@returns: list of found packages
	@rtype: backend.Package[]"""

	try:
		if masked:
			t = portage_settings.porttree.dbapi.xmatch("match-all", search_key)
			t += portage_settings.vartree.dbapi.match(search_key)
		else:
			t = portage_settings.porttree.dbapi.match(search_key)
			t += portage_settings.vartree.dbapi.match(search_key)
	# catch the "ambigous package" Exception
	except ValueError, e:
		if type(e[0]) == types.ListType:
			t = []
			for cp in e[0]:
				if masked:
					t += portage_settings.porttree.dbapi.xmatch("match-all", cp)
					t += portage_settings.vartree.dbapi.match(cp)
				else:
					t += portage_settings.porttree.dbapi.match(cp)
					t += portage_settings.vartree.dbapi.match(cp)
		else:
			raise ValueError(e)
	# Make the list of packages unique
	t = unique_array(t)
	t.sort()
	return geneticize_list(t)

def find_installed_packages (search_key, masked=False):
	"""This returns a list of packages which have to fit exactly. Additionally ranges like '<,>,=,~,!' et. al. are possible.
	
	@param search_key: the key to look for
	@type search_key: string
	@param masked: if True, also look for masked packages
	@type masked: boolean
	
	@returns: list of found packages
	@rtype: backend.Package[]"""

	try:
		t = portage_settings.vartree.dbapi.match(search_key)
	# catch the "ambigous package" Exception
	except ValueError, e:
		if type(e[0]) == types.ListType:
			t = []
			for cp in e[0]:
				t += portage_settings.vartree.dbapi.match(cp)
		else:
			raise ValueError(e)

	return geneticize_list(t)

def find_system_packages ():
	"""Looks for all packages saved as "system-packages".
	
	@returns: a tuple of (resolved_packages, unresolved_packages).
	@rtype: (backend.Package[], backend.Package[])"""

	pkglist = portage_settings.settings.packages
	resolved = []
	unresolved = []
	for x in pkglist:
		cpv = x.strip()
		if len(cpv) and cpv[0] == "*":
			pkg = find_best_match(cpv)
			if pkg:
				resolved.append(pkg)
			else:
				unresolved.append(cpv)
	return (geneticize_list(resolved), geneticize_list(unresolved))

def find_world_packages ():
	"""Looks for all packages saved in the world-file.
	
	@returns: a tuple of (resolved_packages, unresolved_packages).
	@rtype: (backend.Package[], backend.Package[])"""

	f = open(portage.WORLD_FILE)
	pkglist = f.readlines()
	resolved = []
	unresolved = []
	for x in pkglist:
		cpv = x.strip()
		if len(cpv) and cpv[0] != "#":
			pkg = find_best_match(cpv)
			if pkg:
				resolved.append(pkg)
			else:
				unresolved.append(cpv)
	return (geneticize_list(resolved), geneticize_list(unresolved))

def find_all_installed_packages (name=None, withVersion=True):
	"""Finds all installed packages matching a name or all if no name is specified.

	@param name: the name to look for - it is expanded to .*name.* ; if None, all packages are returned
	@type name: string or None
	@param withVersion: if True version-specific packages are returned; else only the cat/package-strings a delivered
	@type withVersion: boolean

	@returns: all packages/cp-strings found
	@rtype: backend.Package[] or cp-string[]"""

	if withVersion:
		t = portage_settings.vartree.dbapi.cpv_all()
		if name:
			t = filter(find_lambda(name),t)
		return geneticize_list(t)
	
	else:
		t = portage_settings.vartree.dbapi.cp_all()
		if name:
			t = filter(find_lambda(name),t)
		return t

def find_all_uninstalled_packages (name=None):
	"""Finds all uninstalled packages matching a name or all if no name is specified.

	@param name: the name to look for - it is expanded to .*name.* ; if None, all packages are returned
	@type name: string or None
	@returns: all packages found
	@rtype: backend.Package[]"""

	alist = find_all_packages(name)
	return geneticize_list([x for x in alist if not x.is_installed()])	

def find_all_packages (name=None, withVersion=True):
	"""Finds all packages matching a name or all if no name is specified.

	@param name: the name to look for - it is expanded to .*name.* ; if None, all packages are returned
	@type name: string or None
	@param withVersion: if True version-specific packages are returned; else only the cat/package-strings a delivered
	@type withVersion: boolean

	@returns: all packages/cp-strings found
	@rtype: backend.Package[] or cp-string[]"""
	
	t = portage_settings.porttree.dbapi.cp_all()
	t += portage_settings.vartree.dbapi.cp_all()
	if name:
		t = filter(find_lambda(name),t)
	t = unique_array(t)
	
	if (withVersion):
		t2 = []
		for x in t:
			t2 += portage_settings.porttree.dbapi.cp_list(x)
			t2 += portage_settings.vartree.dbapi.cp_list(x)
			t2 = unique_array(t2)
		return geneticize_list(t2)
	else:
		return t;

def find_all_world_packages (name=None):
	"""Finds all world packages matching a name or all if no name is specified.

	@param name: the name to look for - it is expanded to .*name.* ; if None, all packages are returned
	@type name: string or None
	@returns: all packages found
	@rtype: backend.Package[]"""

	world = filter(find_lambda(name), [x.get_cpv() for x in find_world_packages()[0]])
	world = unique_array(world)
	return geneticize_list(world)

def find_all_system_packages (name=None):
	"""Finds all system packages matching a name or all if no name is specified.

	@param name: the name to look for - it is expanded to .*name.* ; if None, all packages are returned
	@type name: string or None
	@returns: all packages found
	@rtype: backend.Package[]"""

	sys = filter(find_lambda(name), [x.get_cpv() for x in find_system_packages()[0]])
	sys = unique_array(sys)
	return geneticize_list(sys)

def list_categories (name=None):
	"""Finds all categories matching a name or all if no name is specified.

	@param name: the name to look for - it is expanded to .*name.* ; if None, all categories are returned
	@type name: string or None
	@returns: all categories found
	@rtype: string[]"""

	categories = portage_settings.settings.categories
	return filter(find_lambda(name), categories)

def split_package_name (name):
	"""Splits a package name in its elements.

	@param name: name to split
	@type name: string
	@returns: list: [category, name, version, rev] whereby rev is "r0" if not specified in the name
	@rtype: string[]"""
	
	r = portage.catpkgsplit(portage.dep_getcpv(name))
	if not r:
		r = name.split("/")
		if len(r) == 1:
			return ["", name, "", "r0"]
		else:
			return r + ["", "r0"]
	if r[0] == 'null':
		r[0] = ''
	return r

def sort_package_list(pkglist):
	"""Sorts a package list in the same manner portage does.
	
	@param pkglist: list to sort
	@type pkglist: Packages[]"""
	
	pkglist.sort(package.Package.compare_version)
	return pkglist

def reload_settings ():
	"""Reloads portage."""
	portage_settings.load()

def update_world (newuse = False, deep = False):
	"""Calculates the packages to get updated in an update world.

	@param newuse: Checks if a use-flag has a different state then to install time.
	@type newuse: boolean
	@param deep: Not only check world packages but also there dependencies.
	@type deep: boolean
	@returns: a list containing of the tuple (new_package, old_package)
	@rtype: (backend.Package, backend.Package)[]"""

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
	sys = find_all_system_packages()
	for x in sys:
		if x[0] == "*": # some packages are stored with a '*' at the front - ignore it
			x = x[1:]
		packages.append(x.strip())

	def get_new_packages (packages):
		new_packages = []
		for p in packages:
			inst = find_installed_packages(p)
			if len(inst) > 1:
				myslots = set()
				for i in inst: # get the slots of the installed packages
					myslots.add(i.get_env_var("SLOT"))

				myslots.add(find_best_match(p).get_env_var("SLOT")) # add the slot of the best package in portage
				for slot in myslots:
					new_packages.append(\
							find_best(\
							[x.get_cpv() for x in find_packages("%s:%s" % (i.get_cp(), slot))]\
							))
			else:
				new_packages.append(find_best_match(p))

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
			oldList = find_installed_packages(p.get_slot_cp())
			if oldList: 
				old = oldList[0] # we should only have one package here - else it is a bug
			else:
				oldList = sort_package_list(find_installed_packages(p.get_cp()))
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
				new = set(p.get_settings("USE").split())
				
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
def get_use_desc (flag, package = None):
	"""Returns the description of a specific useflag or None if no desc was found. 
	If a package is given (in the <cat>/<name> format) the local use descriptions are searched too.
	
	@param flag: flag to get the description for
	@type flag: string
	@param package: name of a package: if given local use descriptions are searched too
	@type package: cp-string
	@returns: found description
	@rtype: string"""
	
	# In the first run the dictionaries 'use_descs' and 'local_use_descs' are filled.
	
	# fill cache if needed
	if use_descs == {} or local_use_descs == {}:
		# read use.desc
		fd = open(portage_settings.settings["PORTDIR"]+"/profiles/use.desc")
		for line in fd.readlines():
			line = line.strip()
			if line != "" and line[0] != '#':
				fields = [x.strip() for x in line.split(" - ",1)]
				if len(fields) == 2:
					use_descs[fields[0]] = fields[1]

		# read use.local.desc
		fd = open(portage_settings.settings["PORTDIR"]+"/profiles/use.local.desc")
		for line in fd.readlines():
			line = line.strip()
			if line != "" and line[0] != '#':
				fields = [x.strip() for x in line.split(":",1)]
				if len(fields) == 2:
					if not fields[0] in local_use_descs: # create
						local_use_descs[fields[0]] = {}
					subfields = [x.strip() for x in fields[1].split(" - ",1)]
					if len(subfields) == 2:
						local_use_descs[fields[0]][subfields[0]] = subfields[1]
	
	# start
	desc = None
	if flag in use_descs:
		desc = use_descs[flag]
	if package != None:
		if package in local_use_descs:
			if flag in local_use_descs[package]:
				desc = local_use_descs[package][flag]
	return desc
