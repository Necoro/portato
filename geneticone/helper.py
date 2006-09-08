#!/usr/bin/python

from geneticone import *
import geneticone

import re
import os

import gentoolkit
import portage
from portage_util import unique_array

class BlockedException (Exception):
	pass

class PackageNotFoundException (Exception):
	pass

def find_lambda (name):
	"""Returns the function needed by all the find_all_*-functions. Returns None if no name is given."""
	if name != None:
		return lambda x: re.match(".*"+name+".*",x)
	else:
		return lambda x: True

def geneticize_list (list_of_packages):
	'''to convert the output of each gentoolkit helper function is a list of *geneticone* Package objects
	'''
	cpvs=[x.get_cpv() for x in list_of_packages]
	return [geneticone.Package(x) for x in cpvs]

def find_best_match (search_key, only_installed = False):
	"""Finds the best match in the portage tree."""
	t = None
	if not only_installed:
		t = porttree.dep_bestmatch(search_key)
	else:
		t = vartree.dep_bestmatch(search_key)
	if t:
		return geneticone.Package(t)
	return None

def find_packages (search_key, masked=False):
	"""This returns a list of packages which have to fit exactly. Additionally ranges like '<,>,=,~,!' et. al. are possible."""
	return geneticize_list(gentoolkit.find_packages(search_key, masked))

def find_installed_packages (search_key, masked=False):
	"""This returns a list of installed packages which have to fit exactly. Additionally ranges like '<,>,=,~,!' et. al. are possible.""" 
	return geneticize_list(gentoolkit.find_installed_packages(search_key, masked))

def find_system_packages (name=None):
	"""Returns a list-tuple (resolved_packages, unresolved_packages) for all system packages."""
	list = gentoolkit.find_system_packages()
	return (geneticize_list(list[0]), geneticize_list(list[1]))

def find_world_packages ():
	"""Returns a list-tuple (resolved_packages, unresolved_packages) for all packages in the world-file."""
	list = gentoolkit.find_world_packages()
	return geneticize_list(list[0]),geneticize_list(list[1])

def find_all_installed_packages (name=None):
	"""Returns a list of all installed packages matching ".*name.*". 
	Returns ALL installed packages if name is None."""
	return geneticize_list(gentoolkit.find_all_installed_packages(find_lambda(name)))

def find_all_uninstalled_packages (name=None):
	"""Returns a list of all uninstalled packages matching ".*name.*". 
	Returns ALL uninstalled packages if name is None."""
	return geneticize_list(gentoolkit.find_all_uninstalled_packages(find_lambda(name)))

def find_all_packages (name=None):
	"""Returns a list of all packages matching ".*name.*". 
	Returns ALL packages if name is None."""
	return geneticize_list(gentoolkit.find_all_packages(find_lambda(name)))

def find_all_world_files (name=None):
	"""Returns a list of all world packages matching ".*name.*". 
	Returns ALL world packages if name is None."""
	world = filter(find_lambda(name), [x.get_cpv() for x in find_world_packages()[0]])
	world = unique_array(world)
	return [geneticone.Package(x) for x in world]

def find_all_system_files (name=None):
	"""Returns a list of all system packages matching ".*name.*". 
	Returns ALL system packages if name is None."""
	sys = filter(find_lambda(name), [x.get_cpv() for x in find_system_packages()[0]])
	sys = unique_array(sys)
	return [geneticone.Package(x) for x in sys]

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

def am_i_root ():
	"""Returns True if the current user is root, False otherwise."""
	if os.getuid() == 0:
		return True
	else:
		return False

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
