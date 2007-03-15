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

from portato.helper import debug
from portato.backend import system

import os
from etcproposals.etcproposals_lib import EtcProposals

class PortatoEtcProposals(EtcProposals):
	"""Subclassed EtcProposals using portato.backend.system during __init__."""

	def refresh(self):
		self.clear_cache()
		del self[:] 
		for dir in system.get_global_settings("CONFIG_PROTECT").split():
			self._add_update_proposals(dir)
		self.sort()

def etc_prop (*args, **kwargs):
	"""Entry point for this plugin."""
	l = len(PortatoEtcProposals())
	debug(l,"files to update")

	if l > 0:
		os.system("etc-proposals")
