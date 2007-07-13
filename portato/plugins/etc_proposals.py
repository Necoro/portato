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

from portato.helper import *
from portato.backend import system

from subprocess import Popen
from etcproposals.etcproposals_lib import EtcProposals, __version__

try:
	from etcproposals.etcproposals_info import FRONTEND, VERSIONS
except ImportError:
	FRONTEND = None
	VERSIONS = None

PROG="/usr/sbin/etc-proposals"

class PortatoEtcProposals(EtcProposals):
	"""Subclassed EtcProposals using portato.backend.system during __init__."""

	def refresh(self):
		self.clear_cache()
		del self[:] 
		for dir in system.get_global_settings("CONFIG_PROTECT").split():
			self._add_update_proposals(dir)
		self.sort()

def get_frontend ():
	if FRONTEND is None:
		return ["--frontend", "gtk"]
	else:
		cmds = dict(zip([x.name for x in FRONTEND], [[x.command] for x in FRONTEND]))
		names = [x.shortname for x in VERSIONS] # need this too, because etcproposals stores frontends in FRONTEND which cannot be launched
		
		for f in ["gtk2", "qt4"]:
			if f in names:
				return cmds[f]

def etc_prop (*args, **kwargs):
	"""Entry point for this plugin."""

	if float(__version__) < 1.1:
		l = len(PortatoEtcProposals())
		debug("%s files to update.", l)

		if l > 0:
			Popen(PROG)
	else:
		f = get_frontend()

		if f:
			Popen([PROG, "--fastexit"]+f)
		else:
			error("Cannot start etc-proposals. No graphical frontend installed!")

def etc_prop_menu (*args, **kwargs):
	if am_i_root():
		if float(__version__) < 1.1:
			Popen(PROG)
		else:
			f = get_frontend()

			if f:
				Popen([PROG]+f)
			else:
				error("Cannot start etc-proposals. No graphical frontend installed!")
	else:
		error("Cannot start etc-proposals. Not root!")
