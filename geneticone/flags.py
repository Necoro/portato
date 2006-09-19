#!/usr/bin/python

#
# File: geneticone/flags.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 Necoro d.M.
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by Necoro d.M. <necoro@necoro.net>

import os
import os.path
from subprocess import Popen, PIPE

from geneticone import *

### GENERAL PART ###

def grep (p, path):
	"""Grep runs "egrep" on a given path and looks for occurences of a given package."""
	if not isinstance(p, Package):
		p = Package(p) # assume it is a cpv or a gentoolkit.Package

	command = "egrep -x -n -r -H '^[<>!=~]{0,2}%s(-[0-9].*)?[[:space:]].*$' %s"
	return Popen((command % (p.get_cp(), path)), shell = True, stdout = PIPE).communicate()[0].splitlines()

def get_data(pkg):
	"""This splits up the data of grep() and builds tuples in the format (file,line,criterion,list_of_flags)."""
	flags = []

	# do grep
	list = grep(pkg, USE_PATH)
	
	for i in range(len(list)):
		file, line, fl = tuple(list[i].split(":")) # get file, line and flag-list
		fl = fl.split()
		crit = fl[0]
		fl = fl[1:]
		# stop after first comment
		for i in range(len(fl)):
			if fl[i][0] == "#": #comment - stop here
				fl = fl[:i]
				break
		flags.append((file,line,crit,fl))

	return flags

### USE FLAG PART ###
USE_PATH = os.path.join(portage.USER_CONFIG_PATH,"package.use.go")
USE_PATH_IS_DIR = os.path.isdir(USE_PATH)
useFlags = {} # useFlags in the file
newUseFlags = [] # useFlags as we want them to be: format: (cpv, file, line, useflag, (true if removed from list / false if added))

def set_use_flag (pkg, flag):
	"""Sets the useflag for a given package."""
	if not isinstance(pkg, Package):
		pkg = Package(pkg) # assume cpv or gentoolkit.Package

	cpv = pkg.get_cpv()
	
	# if not saved in useFlags, get it by calling get_data() which calls grep()
	data = None
	if not cpv in useFlags:
		data = get_data(pkg)
		useFlags[cpv] = data
	else:
		data = useFlags[cpv]

	# add a useflag / delete one
	added = False
	for file, line, crit, flags in data:
		if pkg.matches(crit):
			# we have "-flag" and "flag" is in the uselist -> delete "flag"
			if flag[0] == "-" and flag[1:] in flags:
				if added: del newUseFlags[-1] # we currently added it as an extra option - delete it
				added = True
				newUseFlags.append((pkg.get_cpv(), file, line, flag[1:], True))
				break
			# we have "flag" and "-flag" is in the uselist -> delete "-flag"
			elif flag[0] != "-" and "-"+flag in flags:
				if added: del newUseFlags[-1] # we currently added it as an extra option - delete it
				added = True
				newUseFlags.append((pkg.get_cpv(), file, line, "-"+flag, True))
				break
			# add as an extra flag
			else:
				if not added: newUseFlags.append((pkg.get_cpv(), file, line, flag, False))
				added = True
	# create a new line
	if not added:
		if USE_PATH_IS_DIR:
			newUseFlags.append((pkg.get_cpv(), os.path.join(USE_PATH,"geneticone"), -1, flag, False))
		else:
			newUseFlags.append((pkg.get_cpv(), USE_PATH, -1, flag, False))

def write_use_flags ():
	"""This writes our changed useflags into the file."""
	global newUseFlags, useFlags

	def insert (flag, list):
		"""Shortcut for inserting a new flag right after the package-name."""
		list.insert(1,flag)
	
	def remove (flag, list):
		"""Removes a flag."""
		try:
			list.remove(flag)
		except ValueError: # flag is given as flag\n
			list.remove(flag+"\n")
			list.append("\n") #re-insert the newline

		# no more flags there - comment it out
		if len(list) == 1 or list[1][0] in ("#","\n"):
			list[0] = "#"+list[0]
			insert("#removed by geneticone#",list)

	file_cache = {} # cache for having to read the file only once: name->[lines]
	for cpv, file, line, flag, delete in newUseFlags:
		line = int(line) # it is saved as a string so far!
		
		# add new line
		if line == -1:
			msg = "\n#geneticone update#\n=%s %s" % (cpv, flag)
			if not file in file_cache:
				f = open(file, "a")
				f.write(msg)
				f.close()
			else:
				file_cache[file].append(msg)
		# change a line
		else:
			if not file in file_cache:
				# read file
				f = open(file, "r")
				lines = []
				i = 1
				while i < line: # stop at the given line
					lines.append(f.readline())
					i = i+1
				l = f.readline().split(" ")
				# delete or insert
				if delete:
					remove(flag,l)
				else:
					insert(flag,l)
				lines.append(" ".join(l))
				
				# read the rest
				lines.extend(f.readlines())
				
				file_cache[file] = lines
				f.close()
			else: # in cache
				l = file_cache[file][line-1].split(" ")
				if delete:
					remove(flag,l)
				else:
					insert(flag,l)
				file_cache[file][line-1] = " ".join(l)
	
	# write to disk
	for file in file_cache.keys():
		f = open(file, "w")
		f.writelines(file_cache[file])
		f.close()
	# reset
	useFlags = {}
	newUseFlags = []
