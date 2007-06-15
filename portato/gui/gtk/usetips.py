# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/usetips.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from portato.backend import system
from portato.backend.flags import invert_use_flag

from TreeViewTooltips import TreeViewTooltips

class UseTips (TreeViewTooltips):
	"""This class handles the display of the so called use-tips,
	i.e. the tooltips showing the actual use-flags."""

	def __init__ (self, colno, cfg = None):
		"""Constructor.

		@param colno: the number of the column to check
		@type colno: int
		@param cfg: a config to look in, whether we should show the tips or not
		@type cfg: Config"""

		self.colno = colno
		self.cfg = cfg

		TreeViewTooltips.__init__(self)

	def get_tooltip(self, view, column, path):
		
		# check config
		if self.cfg is not None:
			if not self.cfg.get_boolean("useTips", "GTK"):
				return None
		
		store = view.get_model()
		it = store.get_iter(path)

		if store.iter_parent(it) is not None:
			return self.__get_flags(store.get_value(it, self.colno))
		else: # top items - ignore them
			return None

	def __get_flags(self, cpv):
		pkg = system.new_package(cpv)
		enabled = []
		disabled = []
		expanded = set()

		pkg_flags = pkg.get_all_use_flags()
		if not pkg_flags: # no flags - stop here
			return None
		
		pkg_flags.sort()
		for use in pkg_flags:
			exp = pkg.use_expanded(use)
			if exp:
				expanded.add(exp)
			
			else:
				if pkg.is_use_flag_enabled(use):
					enabled.append(use)
				else:
					disabled.append(use)
		
		string = ""
		
		if enabled:
			string = "<b>+%s</b>" % ("\n+".join(enabled),)
			if len(disabled) > 0:
				string = string + "\n"
		
		if disabled:
			string = string+"<i>- %s</i>" % ("\n- ".join(disabled),)

		if expanded:
			string = string+"\n\n"+"\n".join(expanded)

		return string
