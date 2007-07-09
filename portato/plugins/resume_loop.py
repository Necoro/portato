# -*- coding: utf-8 -*-
#
# File: portato/plugins/resume_loop.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import pty
from subprocess import call, STDOUT
from portato.backend import system
from portato.helper import debug

console = None
command = "until emerge --resume --skipfirst; do : ; done"

def set_console (*args, **kwargs):
	global console
	console = kwargs["console"]

def resume_loop (retcode, *args, **kwargs):
	if retcode is None:
		debug("Resume-loop called while process is still running!", warn = True)
	elif retcode == 0:
		# everything ok - ignore
		#pass
		debug("Everything is ok")
	else:
		if console is None:
			debug("No console for the resume loop...")
		else:
			# open tty
			(master, slave) = pty.openpty()
			console.set_pty(master)
			call(command, stdout = slave, stderr = STDOUT, shell = True, env = system.get_environment())
