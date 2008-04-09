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

import pty, time
from subprocess import Popen, STDOUT
from portato.backend import system
from portato.helper import debug, warning

console = None
title_update = None
command = "until emerge --resume --skipfirst; do : ; done"

def set_data (*args, **kwargs):
	global console, title_update
	console = kwargs["console"]
	title_update = kwargs["title_update"]

def resume_loop (retcode, *args, **kwargs):
	if retcode is None:
		warning(_("Resume-loop called while process is still running!"))
	elif retcode == 0:
		# everything ok - ignore
		#pass
		debug("Everything is ok.")
	else:
		if console is None:
			debug("No console for the resume loop...")
		else:
			# open tty
			(master, slave) = pty.openpty()
			console.set_pty(master)
			p = Popen(command, stdout = slave, stderr = STDOUT, shell = True, env = system.get_environment())

			# update titles
			old_title = console.get_window_title()		
			while p and p.poll() is None:
				if title_update : 
					title = console.get_window_title()
					if title != old_title:
						title_update(title)
					time.sleep(0.5)

			if title_update: title_update(None)
