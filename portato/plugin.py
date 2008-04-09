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

"""A module containing the management of the plugin system."""

from __future__ import absolute_import

import os, os.path
from xml.dom.minidom import parse
from lxml import etree
from gettext import lgettext as _

from .constants import PLUGIN_DIR, XSD_LOCATION
from .helper import debug, info, warning, error, flatten

class PluginImportException (ImportError):
	pass

class Options (object):
	"""The <options>-element."""

	__options = ("disabled", "blocking")

	def __init__ (self, options = None):

		self.disabled = False
		self.blocking = False

		if options:
			self.parse(options)

	def parse (self, options):
		for opt in options:
			nodes = opt.childNodes
			type = str(nodes[0].nodeValue.strip())
			if type in self.__options:
				self.set(type, True)

	def get (self, name):
		return self.__getattribute__(name)

	def set (self, name, value):
		return self.__setattr__(name, value)

class Menu:
	"""A single <menu>-element."""
	def __init__ (self, plugin, label, call):
		"""Constructor.

		@param plugin: the plugin this menu belongs to
		@type plugin: Plugin
		@param label: the label to show
		@type label: string
		@param call: the function to call relative to the import statement
		@type call: string

		@raises PluginImportException: if the plugin's import could not be imported"""

		self.label = label
		self.plugin = plugin

		if self.plugin.needs_import(): # get import
			imp = self.plugin.get_import()
			try:
				mod = __import__(imp, globals(), locals(), [call])
			except ImportError:
				raise PluginImportException, imp

			try:
				self.call = eval("mod."+call) # build function
			except AttributeError:
				raise PluginImportException, imp
		else:
			try:
				self.call = eval(call)
			except AttributeError:
				raise PluginImportException, imp

class Connect:
	"""A single <connect>-element."""

	def __init__ (self, hook, type, depend_plugin):
		"""Constructor.

		@param hook: the parent Hook
		@type hook: Hook
		@param type: the type of the connect ("before", "after", "override")
		@type type: string
		@param depend_plugin: a plugin we are dependant on
		@type depend_plugin: string or None"""

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
		@type call: string"""

		self.plugin = plugin
		self.hook = hook
		self.call = call
		self.connects = []

	def parse_connects (self, connects):
		"""This gets a list of <connect>-elements and parses them.
		
		@param connects: the list of <connect>'s
		@type connects: NodeList"""
		
		if not connects: # no connects - assume "before" connect
			self.connects.append(Connect(self, "before", None))
		
		for c in connects:
			type = c.getAttribute("type")
			if type == '': 
				type = "before"

			# get dep_plugin if available
			dep_plugin = None
			if c.hasChildNodes():
				nodes = c.childNodes
				dep_plugin = nodes[0].nodeValue.strip()

			connect = Connect(self, type, dep_plugin)
			self.connects.append(connect)
		
class Plugin:
	"""A complete plugin."""

	(STAT_DISABLED, STAT_TEMP_ENABLED, STAT_ENABLED, STAT_TEMP_DISABLED) = range(4)

	def __init__ (self, file, name, author):
		"""Constructor.

		@param file: the file name of the plugin.xml
		@type file: string
		@param name: the name of the plugin
		@type name: Node
		@param author: the author of the plugin
		@type author: Node"""

		self.file = file
		self.name = name.firstChild.nodeValue.strip()
		self.author = author.firstChild.nodeValue.strip()
		self._import = None
		self.hooks = []
		self.menus = []
		self.options = Options()

		self.status = self.STAT_ENABLED

	def parse_hooks (self, hooks):
		"""Gets an <hooks>-elements and parses it.

		@param hooks: the hooks node
		@type hooks: Node"""

		for h in hooks.getElementsByTagName("hook"):
			hook = Hook(self, str(h.getAttribute("type")), str(h.getAttribute("call")))
			hook.parse_connects(h.getElementsByTagName("connect"))
			self.hooks.append(hook)

	def parse_menus (self, menus):
		"""Get a list of <menu>-elements and parses them.

		@param menus: the menu nodelist
		@type menus: NodeList"""

		if menus:
			for item in menus[0].getElementsByTagName("item"):
				menu = Menu(self, item.firstChild.nodeValue.strip(), str(item.getAttribute("call")))
				self.menus.append(menu)

	def parse_options (self, options):
		if options:
			for o in options:
				self.options.parse(o.getElementsByTagName("option"))

		self.status = self.STAT_DISABLED if self.options.get("disabled") else self.STAT_ENABLED
	
	def set_import (self, imports):
		"""This gets a list of imports and parses them - setting the import needed to call the plugin.

		@param imports: list of imports
		@type imports: NodeList
		
		@raises PluginImportException: if the plugin's import could not be imported"""

		if imports:
			self._import = str(imports[0].firstChild.nodeValue.strip())

			try: # try loading
				mod = __import__(self._import)
				del mod
			except ImportError:
				raise PluginImportException, self._import

	def needs_import (self):
		"""Returns True if an import is required prior to calling the plugin.
		@rtype: bool"""
		return self._import is not None

	def get_import (self):
		"""Returns the module to import.
		@rtype: string"""
		return self._import

	def get_option(self, name):
		return self.options.get(name)

	def set_option (self, name, value):
		return self.options.set(name, value)

	def is_enabled (self):
		return (self.status in (self.STAT_ENABLED, self.STAT_TEMP_ENABLED))

class PluginQueue:
	"""Class managing and loading the plugins."""

	def __init__ (self, frontend, load = True):
		"""Constructor.
		
		@param frontend: the frontend used
		@type frontend: string
		@param load: if False nothing is loaded
		@type load: bool"""

		self.frontend = frontend
		self.list = []
		self.hooks = {}
		if load:
			self._load()

	def get_plugins (self, list_disabled = True):
		return [x for x in self.list if (x.is_enabled() or list_disabled)]

	def get_plugin_data (self, list_disabled = False):
		return [(x.name, x.author) for x in self.list if (x.is_enabled() or list_disabled)]

	def get_plugin_menus (self, list_disabled = False):
		return flatten([x.menus for x in self.list if (x.is_enabled() or list_disabled)])

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
					error(_("%s cannot be imported."), imp)
					return

				try:
					f = eval("mod."+cmd.hook.call) # build function
				except AttributeError:
					error(_("%s cannot be imported."), cmd.hook.call)
			else:
				try:
					f = eval(cmd.hook.call)
				except AttributeError:
					error(_("%s cannot be imported."), cmd.hook.call)

			return f(*hargs, **hkwargs) # call function

		def hook_decorator (func):
			"""This is the real decorator."""
			
			if hook in self.hooks:
				list = self.hooks[hook]
			else:
				list = ([],[],[])

			# remove disabled
			_list = ([],[],[])
			for i in range(len(list)):
				for cmd in list[i]:
					if cmd.hook.plugin.is_enabled():
						_list[i].append(cmd)
			
			list = _list

			def wrapper (*args, **kwargs):
				
				ret = None

				# before
				for cmd in list[0]:
					debug(_("Accessing hook '%(hook)s' of plugin '%(plugin)s' (before)."), {"hook" : hook, "plugin": cmd.hook.plugin.name})
					call(cmd)
				
				if list[1]: # override
					info(_("Overriding hook '%(hook)s' with plugin '%(plugin)s'."), {"hook": hook, "plugin": list[1][0].hook.plugin.name})
					ret = call(list[1][0])
				else: # normal
					ret = func(*args, **kwargs)

				# after
				for cmd in list[2]:
					debug(_("Accessing hook '%(hook)s' of plugin '%(plugin)s' (after)."), {"hook":hook, "plugin": cmd.hook.plugin.name})
					call(cmd)

				return ret

			return wrapper

		return hook_decorator

	def _load (self):
		"""Load the plugins."""
		plugins = filter(lambda x: x.endswith(".xml"), os.listdir(PLUGIN_DIR))
		plugins = map(lambda x: os.path.join(PLUGIN_DIR, x), plugins)
		schema = etree.XMLSchema(file = XSD_LOCATION)

		for p in plugins:
			
			try:
				schema.assertValid(etree.parse(p))
			except etree.XMLSyntaxError:
				error(_("Loading plugin '%s' failed. Invalid XML syntax."), p)
				continue
			except etree.DocumentInvalid:
				error(_("Loading plugin '%s' failed. Plugin does not comply with schema."), p)
				continue

			doc = parse(p)
			
			try:
				list = doc.getElementsByTagName("plugin")
				elem = list[0]

				frontendOK = None
				frontends = elem.getElementsByTagName("frontends")
				if frontends:
					nodes = frontends[0].childNodes
					for f in nodes[0].nodeValue.strip().split():
						if f == self.frontend:
							frontendOK = True # one positive is enough
							break
						elif frontendOK is None: # do not make negative if we already have a positive
							frontendOK = False

				if frontendOK is None or frontendOK == True:
					plugin = Plugin(p, elem.getElementsByTagName("name")[0], elem.getElementsByTagName("author")[0])
					plugin.parse_hooks(elem.getElementsByTagName("hooks")[0])
					plugin.set_import(elem.getElementsByTagName("import"))
					plugin.parse_menus(elem.getElementsByTagName("menu"))
					plugin.parse_options(elem.getElementsByTagName("options"))
				
					self.list.append(plugin)
					info(_("Plugin '%s' loaded."), p)
			
			except PluginImportException, e:
				error(_("Loading plugin '%(plugin)s' failed: Could not import %(import)s"), {"plugin": p, "import": e[0]})
			finally:
				doc.unlink()

		self._organize()

	def _organize (self):
		"""Creates the lists of connects in a way, that all dependencies are fullfilled."""
		unresolved_before = {} 
		unresolved_after = {}
		star_before = {} # should be _before_ all other
		star_after = {} # should be _after_ all other

		for plugin in self.list: # plugins
			for hook in plugin.hooks: # hooks in plugin
				if not hook.hook in self.hooks:
					self.hooks[hook.hook] = ([], [], [])

				for connect in hook.connects: # connects in hook
					
					# type="before"
					if connect.is_before_type():
						if connect.depend_plugin is None: # no dependency -> straight add
							self.hooks[hook.hook][0].append(connect)
						elif connect.depend_plugin == "*":
							self.hooks[hook.hook][0][0:0] = [connect]
						elif connect.depend_plugin == "-*":
							if not hook.hook in star_before:
								star_before[hook.hook] = []

							star_before[hook.hook].append(connect)
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
						elif connect.depend_plugin == "*":
							if not hook.hook in star_after:
								star_after[hook.hook] = []

							star_after[hook.hook].append(connect)
						elif connect.depend_plugin == "-*":
							self.hooks[hook.hook][2][0:0] = [connect]
						else:
							named = [x.hook.plugin.name for x in self.hooks[hook.hook][2]]
							if connect.depend_plugin in named:
								self.hooks[hook.hook][2].insert(named.index(connect.depend_plugin)+1, connect)
							else:
								if not hook.hook in unresolved_after:
									unresolved_after[hook.hook] = []
								
								unresolved_after[hook.hook].append(connect)
					
					# type = "override"
					elif connect.is_override_type():
						if self.hooks[hook.hook][1]:
							warning(_("For hook '%(hook)s' an override is already defined by plugin '%(plugin)s'!"), {"hook": hook.hook, "plugin": self.hooks[hook.hook][1][0]})
						
						self.hooks[hook.hook][1][:1] = [connect]
						continue
		
		self._resolve_unresolved(unresolved_before, unresolved_after)

		for hook in star_before:
			self.hooks[hook][0].extend(star_before[hook]) # append the list

		for hook in star_after:
			self.hooks[hook][2].extend(star_after[hook]) # append the list


	def _resolve_unresolved (self, before, after):
		def resolve(hook, list, idx, add):
			if not list: 
				return
			
			changed = False
			for connect in list[:]:
				named = [x.plugin.name for x in self.hooks[hook][idx]]
				if connect.depend_plugin in named:
					changed = True
					self.hooks[hook][idx].insert(named.index(connect.depend_plugin)+add, connect)
					list.remove(connect)

			if changed:
				resolve(hook, list, idx, add)

			for l in list:
				warning("Command for hook '%(hook)s' in plugin '%(plugin)s' could not be added due to missing dependant: '%(dep)s'!", {"hook": hook, "plugin": l.hook.plugin.name, "dep": l.depend_plugin})

		for hook in before:
			resolve(hook, before[hook], 0, 0)
		
		for hook in after:
			resolve(hook, after[hook], 2, 1)


__plugins = None

def load_plugins(frontend):
	"""Loads the plugins for a given frontend.
	@param frontend: The frontend. See L{constants.FRONTENDS} for the correct list of values.
	@type frontend: string"""

	global __plugins
	if __plugins is None or __plugins.frontend != frontend:
		__plugins = PluginQueue(frontend)

def get_plugin_queue():
	"""Returns the actual L{PluginQueue}. If it is C{None}, they are not being loaded yet.

	@returns: the actual L{PluginQueue} or C{None}
	@rtype: PluginQueue"""
	return __plugins

def hook(hook, *args, **kwargs):
	if __plugins is None:
		def pseudo_decorator(f):
			return f
		return pseudo_decorator
	else:
		return __plugins.hook(hook, *args, **kwargs)
