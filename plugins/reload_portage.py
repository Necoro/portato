# -*- coding: utf-8 -*-
#
# File: plugins/reload_portage.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from portato.backend import system

class ReloadPortage (Plugin):
    __author__ = "René 'Necoro' Neumann"
    __description__ = """Reloads portage when an emerge process has finished.
This can take some time, but sometimes it is necessairy."""
    
    def init(self):
        self.add_call("after_emerge", self.hook, type = "after", dep = "EtcProposals")
        self.status = self.STAT_DISABLED # disable by default
    
    def hook (self, *args, **kwargs):
        system.reload_settings()

register(ReloadPortage)
