# -*- coding: utf-8 -*-
#
# File: plugins/new_version.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from portato.helper import debug, warning

from subprocess import Popen, PIPE
import gobject

from portato import get_listener
from portato.constants import REPOURI, REVISION, APP_ICON, APP
from portato.gui.utils import GtkThread

class NewVersionFinder(WidgetPlugin):
    """
    Checks for a new version of portato every 30 minutes and on startup.
    """
    __author__ = "René 'Necoro' Neumann"
    __dependency__ = ["dev-vcs/git", "dev-python/notify-python"]

    def init (self):
        self.add_call("main", self.run)

    def widget_init (self):
        self.create_widget("Plugin Menu", "Check for new _versions", activate = self.menu)

    def get_notify_callback (self, rev):
        def callback():
            get_listener().send_notify(
                    base = "New Portato Live Version Found",
                    descr = "The most recent revision is %s." % rev,
                    icon = APP_ICON)
            return False

        return callback

    def find_version (self, rev):

        repo, branch = REPOURI.split('::')

        remote_rev = Popen(['git', 'ls-remote', repo, branch], stdout = PIPE).communicate()[0].strip().split('\t')
        
        if len(remote_rev) and remote_rev[1] not in (branch, 'refs/heads/'+branch, 'refs/tags/'+branch):
            warning('NEW_VERSION :: Returned revision information looks strange: %s', str(remote_rev))
        else:
            remote_rev = remote_rev[0]
            debug("NEW_VERSION :: Installed rev: %s - Current rev: %s", rev, remote_rev)

            if rev != remote_rev:
                gobject.idle_add(self.get_notify_callback(remote_rev))

    def start_thread(self, rev):
        t = GtkThread(target = self.find_version, name = "Version Updater Thread", args = (rev,))
        t.setDaemon(True)
        t.start()
        return True

    def menu (self, *args, **kwargs):
        """
        Run the thread once.
        """
        if not REVISION:
            return None
        
        self.start_thread(REVISION)
        return REVISION

    def run (self, *args, **kwargs):
        """
        Run the thread once and add a 30 minutes timer.
        """
        rev = self.menu()

        if rev is not None:
            gobject.timeout_add(30*60*1000, self.start_thread, rev) # call it every 30 minutes

register(NewVersionFinder, REVISION == '')
