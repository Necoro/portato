#
# File: geneticone/backend/portage_helper.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 Necoro d.M.
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by Necoro d.M. <necoro@necoro.net>

import re, os, copy

import portage, gentoolkit
from portage_util import unique_array

from geneticone.backend import *
import package

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
	"""Convertes a list of gentoolkit.Packages into L{backend.Package}s.
	@param list_of_packages: the list of packages
	@type list_of_packages: list of gentoolkit.Packages
	@returns: converted list
	@rtype: list of geneticone.backend.Packages"""
	return [package.Package(x) for x in list_of_packages]

def find_best_match (search_key, only_installed = False):
	"""Finds the best match in the portage tree. It does not find masked packages!
	
	@param search_key: the key to find in the portage tree
	@type search_key: string
	@param only_installed: if True, only installed packages are searched
	@type only_installed: boolean
	
	@returns: the package found or None
	@rtype: backend.Package or None"""

	t = None
	if not only_installed:
		t = porttree.dep_bestmatch(search_key)
	else:
		t = vartree.dep_bestmatch(search_key)
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
	@rtype: list of backend.Package"""

	return geneticize_list(gentoolkit.find_packages(search_key, masked))

def find_installed_packages (search_key, masked=False):
	"""This returns a list of packages which have to fit exactly. Additionally ranges like '<,>,=,~,!' et. al. are possible.
	@param search_key: the key to look for
	@type search_key: string
	@param masked: if True, also look for masked packages
	@type masked: boolean
	@returns: list of found packages
	@rtype: list of backend.Package"""

	return geneticize_list(gentoolkit.find_installed_packages(search_key, masked))

def find_system_packages ():
	"""Returns a list-tuple (resolved_packages, unresolved_packages) for all system packages."""
	list = gentoolkit.find_system_packages()
	return (geneticize_list(list[0]), geneticize_list(list[1]))

def find_world_packages ():
	"""Returns a list-tuple (resolved_packages, unresolved_packages) for all packages in the world-file."""
	list = gentoolkit.find_world_packages()
	return geneticize_list(list[0]),geneticize_list(list[1])

def find_all_installed_packages (name=None, withVersion=True):
	"""Returns a list of all installed packages matching ".*name.*". 
	Returns ALL installed packages if name is None."""
	if withVersion:
		return geneticize_list(gentoolkit.find_all_installed_packages(find_lambda(name)))
	else:
		t = vartree.dbapi.cp_all()
		if name:
			t = filter(find_lambda(name),t)
		return t

def find_all_uninstalled_packages (name=None):
	"""Returns a list of all uninstalled packages matching ".*name.*". 
	Returns ALL uninstalled packages if name is None."""
	return geneticize_list(gentoolkit.find_all_uninstalled_packages(find_lambda(name)))

def find_all_packages (name=None, withVersion = True):
	"""Returns a list of all packages matching ".*name.*". 
	Returns ALL packages if name is None."""
	if (withVersion):
		return geneticize_list(gentoolkit.find_all_packages(find_lambda(name)))
	else:
		t = porttree.dbapi.cp_all()
		t += vartree.dbapi.cp_all()
		t = unique_array(t)
		if name:
			t = filter(find_lambda(name),t)
		return t

def find_all_world_packages (name=None):
	"""Returns a list of all world packages matching ".*name.*". 
	Returns ALL world packages if name is None."""
	world = filter(find_lambda(name), [x.get_cpv() for x in find_world_packages()[0]])
	world = unique_array(world)
	return [package.Package(x) for x in world]

def find_all_system_packages (name=None):
	"""Returns a list of all system packages matching ".*name.*". 
	Returns ALL system packages if name is None."""
	sys = filter(find_lambda(name), [x.get_cpv() for x in find_system_packages()[0]])
	sys = unique_array(sys)
	return [package.Package(x) for x in sys]

def get_all_versions (cp):
	"""Returns all versions of a certain package.
	@param cp: the package
	@type cp: string (cat/pkg)
	@returns: the list of found packages
	@rtype: list of backend.Package"""
	t = porttree.dbapi.cp_list(cp)
	t += vartree.dbapi.cp_list(cp)
	t = unique_array(t)
	return geneticize_list(t)

def get_all_installed_versions (cp):
	"""Returns all installed versions of a certain package.
	@param cp: the package
	@type cp: string (cat/pkg)
	@returns: the list of found packages
	@rtype: list of backend.Package"""
	return geneticize_list(vartree.dbapi.cp_list(cp))

def list_categories (name=None):
	"""Returns a list of categories matching ".*name.*" or all categories."""
	categories = gentoolkit.settings.categories
	return filter(find_lambda(name), categories)

def split_package_name (name):
	"""Returns a list in the form [category, name, version, revision]. Revision will
	be 'r0' if none can be inferred. Category and version will be empty, if none can
	be inferred."""
	return gentoolkit.split_package_name(name)

def sort_package_list(pkglist):
	"""Sorts a package list in the same manner portage does."""
	return gentoolkit.sort_package_list(pkglist)

def reload_settings ():
	"""Reloads portage."""
	gentoolkit.settings = portage.config(config_incrementals = copy.deepcopy(gentoolkit.settings.incrementals))

use_descs = {}
local_use_descs = {}
def get_use_desc (flag, package = None):
	"""Returns the description of a specific useflag or None if no desc was found. 
	If a package is given (in the <cat>/<name> format) the local use descriptions are searched too.
	In the first run the dictionaries 'use_descs' and 'local_use_descs' are filled."""
	# fill cache if needed
	if use_descs == {} or local_use_descs == {}:
		# read use.desc
		fd = open(gentoolkit.settings["PORTDIR"]+"/profiles/use.desc")
		for line in fd.readlines():
			line = line.strip()
			if line != "" and line[0] != '#':
				fields = [x.strip() for x in line.split(" - ",1)]
				if len(fields) == 2:
					use_descs[fields[0]] = fields[1]

		# read use.local.desc
		fd = open(gentoolkit.settings["PORTDIR"]+"/profiles/use.local.desc")
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
