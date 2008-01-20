# -*- coding: utf-8 -*-
#
# File: portato/plugins/etc_proposals.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from portato.helper import error

import os
from subprocess import Popen
from gettext import lgettext as _

PROG=["/usr/sbin/etc-proposals"]

def launch (options = []):
	if os.getuid() == 0:
		Popen(PROG+options)
	else:
		error(_("Cannot start etc-proposals. Not root!"))

def etc_prop (*args, **kwargs):
	"""Entry point for this plugin."""
	launch(["--fastexit"])

def etc_prop_menu (*args, **kwargs):
	launch()
