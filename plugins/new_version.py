# -*- coding: utf-8 -*-
#
# File: plugins/new_version.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

try:
    from bzrlib import plugin, branch
except ImportError:
    plugin = branch =  None
import gobject

from portato.helper import debug, warning
from portato import get_listener
from portato.constants import REPOURI, VERSION, APP_ICON, APP
from portato.gui.utils import GtkThread

class NewVersionFinder(Plugin):
    """
    Checks for a new version of portato every 30 minutes and on startup.
    """
    __author__ = "René 'Necoro' Neumann"
    __dependency__ = ["dev-util/bzr"]

    def init (self):
        self.add_call("main", self.run)
        self.add_menu("Check for new _versions", self.menu)

    def find_version (self, rev):
        try:
            b = branch.Branch.open(REPOURI)
        except Exception, e:
            warning("NEW_VERSION :: Exception occured while accessing the remote branch: %s", str(e))
            return

        debug("NEW_VERSION :: Installed rev: %s - Current rev: %s", rev, b.revno())
        if int(rev) < int(b.revno()):
            def callback():
                get_listener().send_notify(base = "New Portato Live Version Found", descr = "You have rev. %s, but the most recent revision is %s." % (rev, b.revno()), icon = APP_ICON)
                return False
            
            gobject.idle_add(callback)

    def start_thread(self, rev):
        t = GtkThread(target = self.find_version, name = "Version Updater Thread", args = (rev,))
        t.setDaemon(True)
        t.start()
        return True

    def menu (self, *args, **kwargs):
        """
        Run the thread once.
        """
        v = VERSION.split()
        if len(v) != 3:
            return None

        rev = v[-1]

        plugin.load_plugins() # to have lp: addresses parsed
        
        self.start_thread(rev)
        return rev

    def run (self, *args, **kwargs):
        """
        Run the thread once and add a 30 minutes timer.
        """
        rev = self.menu()

        if rev is not None:
            gobject.timeout_add(30*60*1000, self.start_thread, rev) # call it every 30 minutes

register(NewVersionFinder, (branch is None))
