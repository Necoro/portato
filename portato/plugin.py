# -*- coding: utf-8 -*-
#
# File: portato/plugin.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import os, os.path
from xml.dom.minidom import parse

from constants import PLUGIN_DIR
from helper import debug

class ParseException (Exception):
	pass

def error (reason, p):
	reason = "("+reason+")"
	debug("Malformed plugin:", p, reason, minus=1, error = 1)

class Connect:
	"""A single <connect>-element."""

	def __init__ (self, hook, type, depend_plugin):
		"""Constructor.

		@param hook: the parent Hook
		@type hook: Hook
		@param type: the type of the connect ("before", "after", "override")
		@type type: string
		@param depend_plugin: a plugin we are dependant on
		@type depend_plugin: string or None
		
		@raises ParseException: on parsing errors"""

		if not type in ["before", "after", "override"]:
			raise ParseException, "Unknown connect type %s" % type

		self.type = type
		self.hook = hook
		self.depend_plugin = depend_plugin

	def is_before_type (self):
		return self.type == "before"

	def is_after_type (self):
		return self.type == "after"

	def is_override_type (self):
		return self.type == "override"

class Hook:
	"""A single <hook>-element."""

	def __init__ (self, plugin, hook, call):
		"""Constructor.

		@param plugin: the parent Plugin
		@type plugin: Plugin
		@param hook: the hook to add to
		@type hook: string
		@param call: the call to make
		@type call: string

		@raises ParseException: on parsing errors"""

		if not hook: 
			raise ParseException, "hook attribute missing"

		if not call: 
			raise ParseException, "call attribute missing"
		
		self.plugin = plugin
		self.hook = hook
		self.call = call
		self.connects = []

	def parse_connects (self, connects):
		"""This gets a list of <connect>-elements and parses them.
		
		@param connects: the list of <connect>'s
		@type connects: NodeList
		
		@raises ParseException: on parsing errors"""
		
		if not connects:
			raise ParseException, "No connect elements in hook"

		for c in connects:
			type = c.getAttribute("type")
			if type == '': 
				type = "before"

			# get dep_plugin if available
			dep_plugin = None
			if c.hasChildNodes():
				nodes = c.childNodes
				if len(nodes) > 1:
					raise ParseException, "Malformed connect"
				
				if nodes[0].nodeType != nodes[0].TEXT_NODE:
					raise ParseException, "Malformed connect"

				dep_plugin = nodes[0].nodeValue.strip()

			connect = Connect(self, type, dep_plugin)
			self.connects.append(connect)
		
class Plugin:
	"""A complete plugin."""

	def __init__ (self, file, name, author):
		"""Constructor.

		@param file: the file name of the plugin.xml
		@type file: string
		@param name: the name of the plugin
		@type name: string
		@param author: the author of the plugin
		@type author: string"""

		self.file = file
		self.name = name
		self.author = author
		self._import = None
		self.hooks = []

	def parse_hooks (self, hooks):
		"""Gets a list of <hook>-elements and parses them.

		@param hooks: the list of elements
		@type hooks: NodeList
		
		@raises ParseException: on parsing errors"""

		for h in hooks:
			hook = Hook(self, h.getAttribute("hook"), h.getAttribute("call"))
			hook.parse_connects(h.getElementsByTagName("connect"))
			self.hooks.append(hook)

	def set_import (self, imports):
		"""This gets a list of imports and parses them - setting the import needed to call the plugin.

		@param imports: list of imports
		@type imports: NodeList
		
		@raises ParseException: on parsing errors"""

		if len(imports) > 1:
			raise ParseException, "More than one import statement."

		if imports[0].hasChildNodes():
			nodes = imports[0].childNodes
			
			if len(nodes) > 1:
				raise ParseException, "Malformed import"
			
			if nodes[0].nodeType != nodes[0].TEXT_NODE:
				raise ParseException, "Malformed import"

			self._import = nodes[0].nodeValue.strip()

			try: # try loading
				mod = __import__(self._import)
				del mod
			except ImportError:
				raise ParseException, self._import+" cannot be imported"
		else:
			raise ParseException, "Malformed import"

	def needs_import (self):
		"""Returns True if an import is required prior to calling the plugin.
		@rtype: bool"""
		return self._import is not None

	def get_import (self):
		"""Returns the module to import.
		@rtype: string"""
		return self._import

class PluginQueue:
	"""Class managing and loading the plugins."""

	def __init__ (self, load = True):
		"""Constructor.

		@param load: if False nothing is loaded
		@type load: bool"""

		self.list = []
		self.hooks = {}
		if load:
			self._load()

	def get_plugin_data (self):
		return [(x.name, x.author) for x in self.list]

	def hook (self, hook, *hargs, **hkwargs):
		"""This is a method taking care of calling the plugins.
		
		B{Example}::
			
			@pluginQueue.hook("some_hook", data)
			def function (a, b, c):
				orig_call(b,c,data)
			
			def function (a, b, c):
				hook = pluginQueue.hook("some_hook", data)
				hook(orig_call)(b,c,data)

		@param hook: the name of the hook
		@type hook: string"""
			
		def call (cmd):
			"""Convienience function for calling a connect.
			@param cmd: the actual Connect
			@type cmd: Connect"""

			imp = ""
			if cmd.hook.plugin.needs_import(): # get import
				imp = cmd.hook.plugin.get_import()
				try:
					mod = __import__(imp, globals(), locals(), [cmd.hook.call])
				except ImportError:
					debug(imp,"cannot be imported", error = 1)
					return

				f = eval("mod."+cmd.hook.call) # build function
			else:
				f = eval(cmd.hook.call)

			f(*hargs, **hkwargs) # call function

		def hook_decorator (func):
			"""This is the real decorator."""
			if hook in self.hooks:
				list = self.hooks[hook]
			else:
				list = ([],[],[])

			def wrapper (*args, **kwargs):
				
				# before
				for cmd in list[0]:
					debug("Accessing hook '%s' of plugin '%s' (before)" % (hook, cmd.hook.plugin.name))
					call(cmd)
				
				if list[1]: # override
					debug("Overriding hook '%s' with plugin '%s'" % (hook, list[1][0].hook.plugin.name))
					call(list[1][0])
				else: # normal
					func(*args, **kwargs)

				# after
				for cmd in list[2]:
					debug("Accessing hook '%s' of plugin '%s' (after)" % (hook, cmd.hook.plugin.name))
					call(cmd)

			return wrapper

		return hook_decorator

	def _load (self):
		"""Load the plugins."""
		plugins = filter(lambda x: x.endswith(".xml"), os.listdir(PLUGIN_DIR))
		plugins = map(lambda x: os.path.join(PLUGIN_DIR, x), plugins)

		for p in plugins:
			doc = parse(p)
			
			try:
				try:
					list = doc.getElementsByTagName("plugin")
					if len(list) != 1:
						raise ParseException, "Number of plugin elements unequal to 1"
					
					elem = list[0]

					plugin = Plugin(p, elem.getAttribute("name"), elem.getAttribute("author"))
					plugin.parse_hooks(elem.getElementsByTagName("hook"))
					plugin.set_import(elem.getElementsByTagName("import"))
					
					self.list.append(plugin)

				except ParseException, e:
					error(e[0],p)
			finally:
				doc.unlink()

		self._organize()

	def _organize (self):
		"""Creates the lists of connects in a way, that all dependencies are fullfilled."""
		unresolved_before = {} 
		unresolved_after = {}

		for plugin in self.list: # plugins
			for hook in plugin.hooks: # hooks in plugin
				if not hook.hook in self.hooks:
					self.hooks[hook.hook] = ([], [], [])

				for connect in hook.connects: # connects in hook
					
					# type="before"
					if connect.is_before_type():
						if connect.depend_plugin is None: # no dependency -> straight add
							self.hooks[hook.hook][0].append(connect)
						else:
							named = [x.plugin.name for x in self.hooks[hook.hook][0]]
							if connect.depend_plugin in named:
								self.hooks[hook.hook][0].insert(named.index(connect.depend_plugin), connect)
							else:
								if not hook.hook in unresolved_before:
									unresolved_before[hook.hook] = []
								
								unresolved_before[hook.hook].append(connect)

					# type = "after"
					elif connect.is_after_type():
						if connect.depend_plugin is None: # no dependency -> straight add
							self.hooks[hook.hook][2].append(connect)
						else:
							named = [x.plugin.name for x in self.hooks[hook.hook][2]]
							if connect.depend_plugin in named:
								self.hooks[hook.hook][2].insert(named.index(connect.depend_plugin)+1, connect)
							else:
								if not hook.hook in unresolved_after:
									unresolved_after[hook.hook] = []
								
								unresolved_after[hook.hook].append(connect)
					
					# type = "override"
					elif connect.is_override_type():
						if self.hooks[hook.hook][1]:
							debug("For hook '%s' an override is already defined by plugin '%s'!" % (hook.hook, self.hooks[hook.hook][1][0]), warn = 1)
						
						self.hooks[hook.hook][1][:1] = [connect]
						continue
		
		self._resolve_unresolved(unresolved_before, unresolved_after)

	def _resolve_unresolved (self, before, after):
		def resolve(hook, list, idx, add):
			if not list: 
				return
			
			changed = False
			for connect in list:
				named = [x.plugin.name for x in self.hooks[hook][idx]]
				if connect.depend_plugin in named:
					changed = True
					self.hooks[hook][idx].insert(named.index(connect.depend_plugin)+add, connect)
					list.remove(connect)

			if changed:
				resolve(hook, list, idx, add)

			for l in list:
				debug("Command for hook '%s' in plugin '%s' could not be added due to missing dependant: '%s'!"% (hook, l.hook.plugin.name, l.depend_plugin), warn = 1)

		for hook in before:
			resolve(hook, before[hook], 0, 0)
		
		for hook in after:
			resolve(hook, after[hook], 2, 1)


__plugins = None

def load_plugins():
	global __plugins
	if __plugins is None:
		__plugins = PluginQueue()

def get_plugins():
	return __plugins

def hook(hook, *args, **kwargs):
	if __plugins is None:
		def pseudo_decorator(f):
			return f
		return pseudo_decorator
	else:
		return __plugins.hook(hook, *args, **kwargs)
