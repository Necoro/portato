# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/views.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import gtksourceview2
import logging

class HighlightView (gtksourceview2.View):

	def __init__ (self, get_file_fn, languages = []):
		self.get_fn = get_file_fn

		man = gtksourceview2.LanguageManager()
		
		language = None
		old_lang = None
		for lang in languages:
			if old_lang and not language:
				warning(_("No %(old)s language file installed. Falling back to %(new)s."), {"old" : old_lang, "new" : lang})
			language = man.get_language(lang)
			old_lang = lang

		if not language and old_lang:
			warning(_("No %(old)s language file installed. Disable highlighting."), {"old" : old_lang})

		buf = gtksourceview2.Buffer()
		buf.set_language(language)

		gtksourceview2.View.__init__(self, buf)

		self.set_editable(False)
		self.set_cursor_visible(False)
		self.connect("map", self.cb_mapped)

		self.pkg = None
		self.updated = False

	def update (self, pkg):
		self.pkg = pkg
		self.updated = True
		
	def cb_mapped (self, *args):
		if self.updated and self.pkg:
			try:
				with open(self.get_fn(self.pkg)) as f:
					lines = f.readlines()
			except IOError, e:
				lines = _("Error: %s") % e.strerror

			self.get_buffer().set_text("".join(lines))

		return False

class LogView (logging.Handler):

	colors = (
			(logging.DEBUG, "debug", "blue"),
			(logging.INFO, "info", "green"),
			(logging.WARNING, "warning", "yellow"),
			(-1, "error", "red")
			)

	def __init__ (self, view):
		logging.Handler.__init__(self, logging.DEBUG)

		self.view = view
		self.buf = view.get_buffer()

		# set tags
		for lvl, name, color in self.colors:
			self.buf.create_tag("log_%s" % name, foreground = color,weight = pango.WEIGHT_BOLD)
		
		logging.getLogger("portatoLogger").addHandler(self)

	def emit (self, record):
		iter = self.buf.get_end_iter()
		
		for lvl, name, color in self.colors:
			if lvl == -1 or record.levelno <= lvl:
				tag = "log_%s" % name
				break

		self.buf.insert_with_tags_by_name(iter, "* ", tag)
		self.buf.insert_at_cursor(record.getMessage()+"\n")
