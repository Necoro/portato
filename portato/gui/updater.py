# -*- coding: utf-8 -*-
#
# File: portato/gui/updater.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from ..backend import system

import threading, subprocess, time
from ..helper import debug, warning, error

class Updater (object):
    """
    This class is intended to check what package is currently being installed and remove this one from the queue.

    @cvar SED_EXP: The sed expression to strip the package name out of the qlop call.
    """
    
    SED_EXP = r"""
/\*/{
s/ \* //
n
}
d"""
    
    def __init__ (self, queue, iterators, threadClass = threading.Thread):
        """
        Constructor.
        Also directly initializes the thread.

        @param queue: an emerge queue instance
        @type queue: EmergeQueue
        @param iterators: a dictionary of iterators in the current queue
        @type iterators: dict(string->Iterator)
        """
        
        if not issubclass(threadClass, threading.Thread):
            raise ValueError, "Only subclasses of threading.Thread are allowed."

        self.queue = queue
        self.iterators = iterators
        self.threadClass = threadClass
        self.stopEvent = threading.Event()
        self.removed = set()

        t = threadClass(name = "Queue Updater Thread", target = self.run)
        t.setDaemon(True)
        t.start()

    def run (self):
        """
        Run and run and run ...
        Checks the packages until being stopped.
        """

        curr = set()
        while not self.stopEvent.isSet():

            # this = $(qlop -cCq | sed $SED_EXP)
            p1 = subprocess.Popen(["qlop", "--current", "--nocolor", "--quiet"], stdout = subprocess.PIPE)
            this = subprocess.Popen(["sed", self.SED_EXP], stdout = subprocess.PIPE, stdin = p1.stdout).communicate()[0]
            
            this = set(this.split()) if this else set()
            for removed in curr - this:
                self.remove(self.find(removed)) # remove the previous
            curr = this
            
            time.sleep(2.0)

        self.removed = set()
                
    def stop (self):
        """
        Stops the current updater.
        """
        self.stopEvent.set()

    def find (self, pv, masked = False):
        """
        As qlop only returns 'package-version' we need to assign it to a cpv.
        This is done here.
        """

        pkgs = system.find_packages("=%s" % pv, only_cpv = True, masked = masked)

        if len(pkgs) > 1: # ambigous - try to find the one which is also in the iterators
            for p in pkgs:
                if p in self.iterators:
                    return p
        elif not pkgs: # nothing found =|
            if not masked:
                warning(_("No unmasked version of package '%s' found. Trying masked ones. This normally should not happen..."), pv)
                return self.find(pv, True)
            
            else:
                error(_("Trying to remove package '%s' from queue which does not exist in system."), pv)
                return None
        else: # only one choice =)
            return pkgs[0]
    
    def remove (self, cpv):
        """
        Remove a package from the queue.
        """
        
        if cpv is None:
            debug("Nothing to remove.")
            return

        if cpv in self.removed:
            return
        
        self.removed.add(cpv)

        try:
            self.queue.remove_with_children(self.iterators[cpv])
        except KeyError:
            debug("'%s' should be removed, but is not in queue.", cpv)
