# -*- coding: utf-8 -*-
#
# File: portato/config_parser.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from helper import debug

import re
import types

DELIMITER = ["=", ":"]
COMMENT = [";","#"]

# precompiled expressions
TRUE = re.compile("((true)|(1)|(on)|(wahr)|(ja)|(yes))", re.I)
FALSE = re.compile("((false)|(0)|(off)|(falsch)|(nein)|(no))", re.I)
SECTION = re.compile("\s*\[(\w+)\]\s*")
EXPRESSION = re.compile(r"\s*(\w+)\s*[:=]\s*(.*)\s*")

class Value (object):
	"""Class defining a value of a key."""

	def __init__ (self, value, line, bool = None):
		"""Constructor.

		@param value: the value
		@type value: string
		@param line: the line in the config file
		@type line: int
		@param bool: boolean meaning of the value
		@type bool: boolean"""

		self.__value = value
		self.line = line
		self.boolean = bool
		
		self.changed = False # true if we changed it
		self.old = value # keep the original one ... so if we change it back to this one, we do not have to write

	def set (self, value):
		"""Sets the value to a new one.
		
		@param value: new value
		@type value: string"""

		self.__value = value
		
		if value != self.old:
			self.changed = True
		else:
			self.changed = False

	def get (self):
		"""Returns the actual value.
		
		@returns: the actual value
		@rtype: string"""

		return self.__value
	
	def is_bool (self):
		"""Returns whether the actual value has a boolean meaning.
		
		@returns: True if the actual value can be interpreted as a boolean
		@rtype: boolean"""

		return (self.boolean != None)

	def __str__ (self):
		return str(self.__value)

	def __repr__ (self):
		return self.__str__()
	
	value = property(get,set)
	
class ConfigParser:
	"""The newly implemented Config-Parser."""

	# generates the complementary true-false-pairs
	true_false = {
				"true" 	: "false",
				"1"		: "0",
				"on"	: "off",
				"yes"	: "no",
				"ja"	: "nein",
				"wahr"	: "falsch"}
	true_false.update(zip(true_false.values(), true_false.keys()))

	def __init__ (self, file):
		"""Constructor.

		@param file: the configuration file to open
		@type file: string"""

		self.file = file
		self.__initialize()

	def __initialize (self):
		"""Private method which initializes our dictionaries."""

		self.vars = {"MAIN": {}}
		self.cache = None # file cache
		self.pos = {} # stores the positions of the matches

	def _invert (self, val):
		"""Invertes a given boolean.

		@param val: value to invert
		@type val: string
		@returns: inverted value
		@rtype: string"""

		return self.true_false[val.lower()]

	def parse (self):
		"""Parses the file."""

		# read into cache
		file = open(self.file, "r")
		self.cache = file.readlines()
		file.close()

		# implicit first section is main
		section = "MAIN"
		count = -1
		for line in self.cache:
			count += 1

			ls = line.strip()
			if not ls: continue # empty
			if ls[0] in COMMENT: continue # comment
			
			# look for a section
			match = SECTION.search(line)
			if match:
				sec = match.group(1).upper()
				if sec != section:
					self.vars[sec] = {}
					section = sec
				continue

			# look for an expression
			match = EXPRESSION.search(line)
			if match: 
				val = match.group(2)
				
				# find the boolean value
				bool = None
				if TRUE.match(val):
					bool = True
				elif FALSE.match(val):
					bool = False
				
				# insert
				key = match.group(1).lower()
				self.vars[section][key] = Value(val, count, bool = bool)
				self.pos[count] = match.span(2)
			else: # neither comment nor empty nor expression nor section => error
				debug("Unrecognized line:",line)

	def get (self, key, section = "MAIN"):
		"""Returns the value of a given key in a section.

		@param key: the key
		@type key: string
		@param section: the section
		@type section: string
		
		@returns: value
		@rtype: string
		
		@raises KeyError: if section or key could not be found"""

		section = section.upper()
		key = key.lower()
		return self.vars[section][key].value

	def get_boolean (self, key, section = "MAIN"):
		"""Returns the boolean value of a given key in a section.

		@param key: the key
		@type key: string
		@param section: the section
		@type section: string
		
		@returns: value
		@rtype: boolean
		
		@raises KeyError: if section or key could not be found
		@raises ValueError: if key does not have a boolean value"""
		
		section = section.upper()
		key = key.lower()

		val = self.vars[section][key]

		if val.is_bool():
			return val.boolean

		raise ValueError, "\"%s\" is not a boolean." % key

	def set (self, key, value = "", section = "MAIN"):
		"""Sets a new value of a given key in a section.

		@param key: the key
		@type key: string
		@param value: the new value
		@type value: string
		@param section: the section
		@type section: string
		
		@raises KeyError: if section or key could not be found"""
		
		section = section.upper()
		key = key.lower()

		self.vars[section][key].value = value

	def set_boolean (self, key, value, section = "MAIN"):
		"""Sets a new boolean value of a given key in a section.
		Therefore it invertes the string representation of the boolean (in lowercase).

		@param key: the key
		@type key: string
		@param value: the new value
		@type value: boolean
		@param section: the section
		@type section: string
		
		@raises KeyError: if section or key could not be found
		@raises ValueError: if the old/new value is not a boolean"""
		
		section = section.upper()
		key = key.lower()
		
		if not isinstance(value, types.BooleanType):
			raise ValueError, "Passed value must be a boolean."

		val = self.vars[section][key]
		if val.is_bool():
			if value is not val.boolean:
				val.boolean = value
				val.value = self._invert(val.value)
		else:
			raise ValueError, "\"%s\" is not a boolean." % key

	def write (self):
		"""Writes file."""

		for sec in self.vars:
			for key in self.vars[sec]:
				val = self.vars[sec][key]
				if val.changed:
					part1 = self.cache[val.line][:self.pos[val.line][0]] 	# key+DELIMITER
					part2 = val.value										# value
					part3 = self.cache[val.line][self.pos[val.line][1]:]	# everything behind the vale (\n in normal cases)
					self.cache[val.line] = part1 + part2 + part3
		
		# write
		f = open(self.file, "w")
		f.writelines(self.cache)
		f.close()

		# reload
		self.__initialize()
		self.parse()
