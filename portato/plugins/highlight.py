# -*- coding: utf-8 -*-
#
# File: portato/plugins/highlight.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from portato.gui.gtk.windows import EbuildWindow

import gtksourceview

class HighlightedEbuildWindow (EbuildWindow):
	"""An ebuild window with syntax highlighting, using the GtkSourceview."""

	def __init__ (self, package, parent):
		self.__class__.__name__ = "EbuildWindow" # make the Window-Class render the correct window
		EbuildWindow.__init__(self, parent, package)

	def _build_view (self):
		# get language
		man = gtksourceview.SourceLanguagesManager()
		language = [l for l in man.get_available_languages() if l.get_name() == "Gentoo"]
		
		# set buffer and view
		self.buf = gtksourceview.SourceBuffer()
		self.buf.set_language(language[0])
		self.buf.set_highlight(True)
		self.view = gtksourceview.SourceView(self.buf)
