# -*- coding: utf-8 -*-
#
# File: portato/plugin.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from collections import defaultdict
from functools import wraps

from .helper import debug, warning, info

class Menu (object):
	__slots__ = ("label", "call")

	def __init__ (self, label, call):
		self.label = label
		self.call = call

class Call (object):
	__slots__ = ("plugin", "hook", "call", "type", "dep")

	def __init__ (self, plugin, hook, call, type = "before", dep = None):
		self.plugin = plugin
		self.hook = hook
		self.call = call
		self.type = type
		self.dep = dep

class Hook (object):
	__slots__ = ("before", "override", "after")

	def __init__ (self):
		self.before = []
		self.override = None
		self.after = []

class Plugin (object):

	(STAT_DISABLED, STAT_TEMP_ENABLED, STAT_ENABLED, STAT_TEMP_DISABLED) = range(4)

	def __init__ (self):
		self.__menus = []
		self.__calls = []
		self.state = STAT_ENABLED

	@property
	def author (self):
		return getattr(self, "__author__", "")

	@property
	def description (self):
		if hasattr(self, "__description__"):
			return self.__description__
		else:
			return getattr(self, "__doc__", "")

	@property
	def name (self):
		return getattr(self, "__name__", self.__class__.__name__)

	@property
	def menus (self):
		return iter(self.__menus)

	@property
	def calls (self):
		return iter(self.__calls)

	def add_menu (self, label, callable):
		self.__menus.append(Menu(label, callable))

	def add_call (self, hook, callable, type = "before", dep = None):
		self.__calls.append(Call(self, hook, callable, type, dep))

	def is_enabled (self):
		return (self.status in (self.STAT_ENABLED, self.STAT_TEMP_ENABLED))

class PluginQueue (object):
	"""Class managing and loading the plugins."""

	def __init__ (self):
		"""
		Constructor.
		"""

		self.plugins = []
		self.hooks = defaultdict(Hook)
		self._load()

	def get_plugins (self, list_disabled = True):
		return (x for x in self.plugins if (x.is_enabled() or list_disabled))

	def _load (self):
		"""Load the plugins."""
		self._organize()

	def add (self, plugin):
		self.plugins.append(plugin)

	def hook (self, hook, *hargs, **hkwargs):

		def hook_decorator (func):
			h = self.hooks.hook

			active = Hook()

			# remove disabled
			for type in ("before", "after"):
				calls = getattr(h, type)
				aCalls = getattr(active, type)
				for call in calls:
					if call.plugin.is_enabled():
						aCalls.append(call)

			if h.override and h.override.plugin.is_enabled():
				active.override = h.override

			@wraps(func)
			def wrapper (*args, **kwargs):
				ret = None

				# before
				for call in active.before:
					debug("Accessing hook '%(hook)s' of plugin '%(plugin)s' (before).", {"hook" : hook, "plugin": call.plugin.name})
					call.call(*hargs, **hkwargs)
				
				if active.override: # override
					info(_("Overriding hook '%(hook)s' with plugin '%(plugin)s'."), {"hook": hook, "plugin": active.override.plugin.name})
					ret = active.override.call(*hargs, **hkwargs)
				else: # normal
					ret = func(*args, **kwargs)

				# after
				for call in active.after:
					debug("Accessing hook '%(hook)s' of plugin '%(plugin)s' (after).", {"hook": hook, "plugin": call.plugin.name})
					call.call(*hargs, **hkwargs)

				return ret

			return wrapper

		return hook_decorator

	def _organize (self):
		"""Creates the lists of connects in a way, that all dependencies are fullfilled."""
		unresolved_before = defaultdict(list)
		unresolved_after = defaultdict(list)
		star_before = defaultdict(Hook) # should be _before_ all other
		star_after = defaultdict(Hook) # should be _after_ all other

		for plugin in self.plugins: # plugins
			for call in plugin.calls: # hooks in plugin
				if call.type == "before":
					if call.dep is None: # no dependency -> straight add
						self.hooks[call.hook].before.append(call)
					elif call.dep == "*":
						self.hooks[call.hook].before.insert(0, call)
					elif call.dep == "-*":
						star_before[call.hook].append(call)
					else:
						named = [x.plugin.name for x in self.hooks[call.hook].before]
						if call.dep in named:
							self.hooks[call.hook].before.insert(named.index(call.dep), call)
						else:
							unresolved_before[call.hook].append(call)

				elif call.type == "after":
					if call.dep is None: # no dependency -> straight add
						self.hooks[call.hook].after.append(call)
					elif call.dep == "*":
						star_after[call.hook].append(call)
					elif call.dep == "-*":
						self.hooks[call.hook].after.insert(0, call)
					else:
						named = [x.plugin.name for x in self.hooks[call.hook].after]
						if call.dep in named:
							self.hooks[call.hook].after.insert(named.index(call.dep)+1, call)
						else:
							unresolved_after[call.hook].append(call)
				
				# type = "override"
				elif call.type == "override":
					if self.hooks[call.hook].override:
						warning(_("For hook '%(hook)s' an override is already defined by plugin '%(plugin)s'!"), {"hook": call.hook, "plugin": self.hooks[call.hook].override.plugin.name})
						warning(_("It is now replaced by the one from plugin '%s'!"), call.plugin.name)
					
					self.hooks[call.hook].override = call
					continue
		
		self._resolve_unresolved(unresolved_before, unresolved_after)

		for hook, calls in star_before.iteritems():
			self.hooks[hook].before.extend(calls) # append the list

		for hook, calls in star_after.iteritems():
			self.hooks[hook].after.extend(calls) # append the list


	def _resolve_unresolved (self, before, after):
		def resolve(hook, list, type, add):
			if not list: 
				return
			
			callList = getattr(self.hooks[hook], type)
			named = [x.plugin.name for x in callList]

			while list and named:
				newNamed = [] # use newNamed, so in each iteration only the plugins inserted last are searched
				for call in list[:]:
					if call.dep in named:
						callList.insert(named.index(call.dep)+add, call)
						list.remove(call)
						newNamed.append(call.plugin.name)

				named = newNamed

			for l in list:
				warning(_("Command for hook '%(hook)s' in plugin '%(plugin)s' could not be added due to missing dependant: '%(dep)s'!"), {"hook": hook, "plugin": l.plugin.name, "dep": l.dep})

		for hook in before:
			resolve(hook, before[hook], "before", 0)
		
		for hook in after:
			resolve(hook, after[hook], "after", 1)


__plugins = None

def load_plugins():
	"""
	Loads the plugins.
	"""
	
	global __plugins
	if __plugins is None:
		__plugins = PluginQueue()

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

def register (plugin):
	if __plugins is not None:
		__plugins.add(plugin)
