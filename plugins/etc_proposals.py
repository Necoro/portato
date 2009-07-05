# -*- coding: utf-8 -*-
#
# File: plugins/etc_proposals.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from portato.helper import error

import os
from subprocess import Popen

class EtcProposals (WidgetPlugin):
    __author__ = "René 'Necoro' Neumann"
    __description__ = "Adds support for <b>etc-proposals</b>, a graphical etc-update replacement."
    __dependency__ = ["app-portage/etc-proposals"]

    def init (self):
        self.prog = ["/usr/sbin/etc-proposals"]
        self.add_call("after_emerge", self.hook, type = "after")

    def widget_init(self):
        self.create_widget("Plugin Menu", "Et_c-Proposals", activate = self.menu)

    def launch (self, options = []):
        if os.getuid() == 0:
            Popen(self.prog+options)
        else:
            error("ETC_PROPOSALS :: %s",_("Cannot start etc-proposals. Not root!"))

    def hook (self, *args, **kwargs):
        """Entry point for this plugin."""
        self.launch(["--fastexit"])

    def menu (self, *args):
        self.launch()

register(EtcProposals)
