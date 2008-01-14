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

import pango
import gtksourceview2
import gtk
import logging

from gettext import lgettext as _

class LazyView (object):
	def __init__ (self):
		self.connect("map", self.cb_mapped)

		self.pkg = None
		self.updated = False

	def update (self, pkg, force = False):
		self.pkg = pkg
		self.updated = True
		
		if force:
			self.cb_mapped()

	def cb_mapped (self, *args):
		if self.updated and self.pkg:
			self.set_text("".join(self._get_content()))
			self.updated = False

		return False

	def set_text (self, text):
		raise NotImplementedError

	def _get_content (self):
		raise NotImplementedError

class ListView (gtk.TextView, LazyView):

	def __init__ (self, content_fn):
		self.content_fn = content_fn

		gtk.TextView.__init__(self)
		LazyView.__init__(self)

		self.set_editable(False)
		self.set_cursor_visible(False)

	def set_text (self, text):
		self.get_buffer().set_text(text)

	def _get_content (self):
		return self.content_fn(self.pkg)

class InstalledOnlyView (ListView):
	def _get_content (self):
		if self.pkg:
			if not self.pkg.is_installed():
				return _("Package is not installed")
			else:
				return ListView._get_content(self)
		else:
			return "Huh?"

class HighlightView (gtksourceview2.View, LazyView):

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
		LazyView.__init__(self)

		self.set_editable(False)
		self.set_cursor_visible(False)

	def set_text (self, text):
		self.get_buffer().set_text(text)
	
	def _get_content (self):
		try:
			with open(self.get_fn(self.pkg)) as f:
				return f.readlines()
		except IOError, e:
			return _("Error: %s") % e.strerror
	
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
