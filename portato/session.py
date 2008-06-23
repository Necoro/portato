# -*- coding: utf-8 -*-
#
# File: portato/session.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import os, os.path

from .config_parser import ConfigParser
from .constants import SESSION_DIR
from .helper import debug, info

class Session (ConfigParser):
	"""
	A small class allowing to save certain states of a program.
	This class works in a quite abstract manner, as it works with handlers, which
	define what options to use out of the config file and how to apply them to the program.

	Note: This class currently does not work with boolean config options. If you
	want to define boolean values, use 0 and 1. This is future proof.
	"""

	# the current session format version
	VERSION = 1

	def __init__ (self, file):
		"""
		Initialize a session with a certain file inside L{SESSION_DIR}.

		@param file: the file in L{SESSION_DIR}, where the options will be saved.
		"""

		self._handlers = []

		if not (os.path.exists(SESSION_DIR) and os.path.isdir(SESSION_DIR)):
			os.mkdir(SESSION_DIR)
		
		ConfigParser.__init__(self, os.path.join(SESSION_DIR, file))
		info(_("Loading session from '%s'.") % self.file)

		try:
			self.parse()
		except IOError, e:
			if e.errno == 2: pass
			else: raise

		# add version check
		self.add_handler(([("version", "session")], self.check_version, lambda: self.VERSION))

	def add_handler (self, (options, load_fn, save_fn), default = None):
		"""
		Adds a handler to this session. A handler is a three-tuple consisting of:
			- a list of (key,section) values
			- a function getting number of option arguments and applying them to the program
			- a function returning the number of option return values - getting them out of the program
		"""
		self._handlers.append((options, load_fn, save_fn, default))

	def load (self):
		"""
		Loads and applies all values of the session.
		"""
		for options, lfn, sfn, default in self._handlers:
			try:
				loaded = [self.get(*x) for x in options]
			except KeyError: # does not exist -> ignore
				debug("No values for %s.", options)
			else:
				debug("Loading %s with values %s.", options, loaded)
				lfn(*loaded)
				continue

			if default:
				debug("Loading %s with defaults %s.", options, default)
				lfn(*default)

	def save (self):
		"""
		Saves all options into the file.
		"""

		for options, lfn, sfn, default in self._handlers:
			vals = sfn()
			
			# map into list if necessairy
			if not hasattr(vals, "__iter__"):
				vals = [vals]
			debug("Saving %s with values %s", options, vals)

			for value, (option, section) in zip(vals, options):
				self.add_section(section)
				self.add(option, str(value), section = section, with_blankline = False)
		
		self.write()

	def check_version (self, vers):
		pass # do nothing atm
