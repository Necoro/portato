# -*- coding: utf-8 -*-
#
# File: portato/config_parser.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

"""
A simple parser for configuration files in ini-style.

The main difference to other simple ini-parsers is, that it does not
write the whole structure into the file, but only the changed values.
Thus it keeps comments and structuring of the file.

:Variables:

	DELIMITER : string[]
		list of delimiters allowed

	COMMENT : string []
		comment marks allowed

	TRUE
		Regular expression for all TRUE values allowed.
		Currently supported are the values (case insensitive): true, 1, on, wahr, ja, yes.

	FALSE
		Regular expression for all FALSE values allowed.
		Currently supported are the values (case insensitive): false, 0, off, falsch, nein, no.

	SECTION
		Regular expression allowing the recognition of a section header.

	EXPRESSION
		Regular expression defining a normal option-value pair.
"""

from __future__ import absolute_import, with_statement
__docformat__ = "restructuredtext"

import re
from gettext import lgettext as _
from threading import Lock

from .helper import debug, error

DELIMITER = ["=", ":"]
COMMENT = [";","#"]

# precompiled expressions
TRUE = re.compile("((true)|(1)|(on)|(wahr)|(ja)|(yes))", re.I)
FALSE = re.compile("((false)|(0)|(off)|(falsch)|(nein)|(no))", re.I)
SECTION = re.compile("\s*\[(?P<name>\w(\w|[-_])*)\]\s*")
EXPRESSION = re.compile(r"\s*(?P<key>\w(\w|[-_])*)\s*[:=]\s*(?P<value>.*)\s*")

class Value (object):
	"""
	Class defining a value of a key.
	
	:IVariables:

		value
			The specific value.

		old
			The old value

		line : int
			The line in the config file.
		
		boolean : boolean
			The boolean meaning of this value. Set this to ``None`` if this is not a boolean.
	
		changed : boolean
			Set to True if the value has been changed.
	"""
	

	def __init__ (self, value, line, bool = None):
		"""
		Constructor.

		:Parameters:

			value : string
				the value

			line : int
				the line in the config file

			bool : boolean
				The boolean meaning of the value. Set this to ``None`` if this is not a boolean.
		"""

		self.__value = value
		self.line = line
		self.boolean = bool
		
		self.changed = False # true if we changed it
		self.old = value # keep the original one ... so if we change it back to this one, we do not have to write

	def set (self, value):
		"""
		Sets the value to a new one.
		
		:param value: new value
		:type value: string
		"""

		self.__value = value
		
		if value != self.old:
			self.changed = True
		else:
			self.changed = False

	def get (self):
		"""
		Returns the actual value.
		
		:rtype: string
		"""

		return self.__value
	
	def is_bool (self):
		"""
		Returns whether the actual value has a boolean meaning.
		
		:rtype: boolean
		"""

		return (self.boolean != None)

	def __str__ (self):
		return str(self.__value)

	def __repr__ (self):
		return self.__str__()
	
	value = property(get,set)
	
class ConfigParser:
	"""
	The parser class.

	:CVariables:

		true_false : string -> string
			A mapping from the truth values to their opposits.
	
	:IVariables:

		file : string
			the file to scan
		cache : string[]
			caches the content of the file
		vars : string -> (string -> `Value`)
			the found options grouped by section
		pos : int -> (int, int)
			the positions of the values grouped by lineno
	"""

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
		"""
		Constructor.

		:param file: the configuration file to open
		:type file: string
		"""

		self.file = file
		self.writelock = Lock()
		self.__initialize()

	def __initialize (self):
		"""Private method which initializes our dictionaries."""

		self.vars = {"MAIN": {}}
		self.cache = [] # file cache
		self.pos = {} # stores the positions of the matches
		self.sections = {"MAIN" : -1} # the line with the section header

	def _invert (self, val):
		"""
		Invertes a given boolean.

		:param val: value to invert
		:type val: string
		:returns: inverted value
		:rtype: string

		:see: `true_false`
		"""

		return self.true_false[val.lower()]

	def parse (self):
		"""Parses the file."""

		# read into cache
		with open(self.file, "r") as f:
			self.cache = f.readlines()

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
				sec = match.group("name").upper()
				self.sections[sec] = count
				if sec != section:
					self.vars[sec] = {}
					section = sec
				continue

			# look for an expression
			match = EXPRESSION.search(line)
			if match: 
				val = match.group("value")
				
				# find the boolean value
				bool = None
				if TRUE.match(val):
					bool = True
				elif FALSE.match(val):
					bool = False
				
				# insert
				key = match.group("key").lower()
				self.vars[section][key] = Value(val, count, bool = bool)
				self.pos[count] = match.span("value")
			else: # neither comment nor empty nor expression nor section => error
				error(_("Unrecognized line in configuration: %s"), line)

	def get (self, key, section = "MAIN"):
		"""
		Returns the value of a given key in a section.

		:Parameters:

			key : string
				the key
			section : string
				the section
		
		:returns: value
		:rtype: string
		
		:raises KeyError: if section or key could not be found
		"""

		section = section.upper()
		key = key.lower()
		return self.vars[section][key].value

	def get_boolean (self, key, section = "MAIN"):
		"""
		Returns the boolean value of a given key in a section.

		:Parameters:

			key : string
				the key
			section : string
				the section
		
		:returns: value
		:rtype: boolean
		
		:raises KeyError: if section or key could not be found
		:raises ValueError: if key does not have a boolean value
		"""
		
		section = section.upper()
		key = key.lower()

		val = self.vars[section][key]

		if val.is_bool():
			return val.boolean

		raise ValueError, "\"%s\" is not a boolean. (%s)" % (key, val.value)

	def set (self, key, value = "", section = "MAIN"):
		"""
		Sets a new value of a given key in a section.

		:Parameters:

			key : string
				the key
			value : string
				the new value
			section : string
				the section
		
		:raises KeyError: if section or key could not be found
		"""
		
		section = section.upper()
		key = key.lower()

		self.vars[section][key].value = value

	def set_boolean (self, key, value, section = "MAIN"):
		"""
		Sets a new boolean value of a given key in a section.
		Therefore it invertes the string representation of the boolean (in lowercase).

		:Parameters:

			key : string
				the key
			value : boolean
				the new value
			section : string
				the section

		:raises KeyError: if section or key could not be found
		:raises ValueError: if the old/new value is not a boolean"""
		
		section = section.upper()
		key = key.lower()
		
		if not isinstance(value, bool):
			raise ValueError, "Passed value must be a boolean."

		val = self.vars[section][key]
		if val.is_bool():
			if value is not val.boolean:
				val.boolean = value
				val.value = self._invert(val.value)
		else:
			raise ValueError, "\"%s\" is not a boolean." % key

	def add_section (self, section, comment = None, with_blankline = True):
		section = section.upper()

		if section in self.vars:
			return

		if with_blankline and len(self.cache) > 0:
			self.cache.append("\n")

		if comment:
			if isinstance(comment, str) or isinstance(comment, unicode):
				comment = comment.split("\n")
			
			comment.insert(0, "")
			comment.append("")
			
			for c in comment:
				self.cache.append("# %s\n" % c)

		self.vars[section] = {}
		self.sections[section] = len(self.cache)
		self.cache.append("[%s]\n" % section)

	def add (self, key, value, section = "MAIN", comment = None, with_blankline = True):
		section = section.upper()
		key = key.lower()

		if key in self.vars[section]:
			return self.set(key, value, section)

		self.write()
		
		# find line# to add
		if self.vars[section]:
			mline = max((x.line for x in self.vars[section].itervalues())) + 1
		else:
			mline = self.sections[section] + 1

		if with_blankline and mline > 0:
			self.cache.insert(mline, "\n")
			mline += 1

		if comment:
			if isinstance(comment, str) or isinstance(comment, unicode):
				comment = comment.split("\n")
			
			for c in comment:
				self.cache.insert(mline, "; %s\n" % c)
				mline += 1
		
		self.cache.insert(mline, "%s = %s\n" % (key, value))
		
		self.write()

	def write (self):
		"""Writes file."""

		if not self.cache:
			return

		with self.writelock:
			for sec in self.vars:
				for val in self.vars[sec].itervalues():
					if val.changed:
						part1 = self.cache[val.line][:self.pos[val.line][0]] 	# key+DELIMITER
						part2 = val.value										# value
						part3 = self.cache[val.line][self.pos[val.line][1]:]	# everything behind the vale (\n in normal cases)

						if not val.old: # empty original value
							add = ""
							if part1.endswith("\n"):
								part1 = part1[:-1]
								add = "\n"
							part3 = part3 + add

						self.cache[val.line] = part1 + part2 + part3
			
			# write
			with open(self.file, "w") as f:
				f.writelines(self.cache)

			# reload
			self.__initialize()
			self.parse()
