# -*- coding: utf-8 -*-
#
# File: portato/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import logging
import sys
import os

class OutputFormatter (logging.Formatter):

	colors = { 
			"blue"	: 34,
			"green"	: 32,
			"red"	: 31,
			"yellow": 33
			}

	def __init__(self, *args, **kwargs):
		logging.Formatter.__init__(self, *args, **kwargs)

		for key, value in self.colors.iteritems():
			self.colors[key] = "\x1b[01;%02dm*\x1b[39;49;00m" % value

	def format (self, record):
		string = logging.Formatter.format(self, record)
		color = None

		if os.isatty(sys.stderr.fileno()):
			if record.levelno <= logging.DEBUG:
				color = self.colors["blue"]
			elif record.levelno <= logging.INFO:
				color = self.colors["green"]
			elif record.levelno <= logging.WARNING:
				color = self.colors["yellow"]
			else:
				color = self.colors["red"]
		else:
			color = "%s:" % record.levelname

		return "%s %s" % (color, string)

# set the whole logging stuff
formatter = OutputFormatter("%(message)s (%(filename)s:%(lineno)s)")

handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.getLogger("portatoLogger").addHandler(handler)
logging.getLogger("portatoLogger").setLevel(logging.DEBUG)
logging.getLogger("portatoLogger").propagate = False

from plistener import PListener
listener = PListener()
