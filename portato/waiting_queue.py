# -*- coding: utf-8 -*-
#
# File: portato/waiting_queue.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from threading import Thread, Event
from Queue import Queue

class WaitingQueue (Queue):

    def __init__ (self, setTrue = True, threadClass = Thread):
        if not issubclass(threadClass, Thread):
            raise ValueError, "Only subclasses of threading.Thread are allowed."
        
        Queue.__init__(self)
        self.event = Event()
        self.counter = 0
        self.threadClass = threadClass

        if setTrue:
            self.event.set() # true at the beginning

        waitingThread = self.threadClass(name = "Waiting-Queue-Thread", target = self.runThread)
        waitingThread.setDaemon(True)
        waitingThread.start()

    def put (self, method, *args, **kwargs):
        self.counter += 1;
        
        try:
            name = "Waiting Thread #%d (called by:%s)" % (self.counter, kwargs.pop("caller"))
        except KeyError:
            name = "Waiting Thread #%d" % self.counter

        t = self.threadClass(name = name, target = method, args = args, kwargs = kwargs)
        t.setDaemon(True)
        Queue.put(self, t, False)

    def runThread (self):
        while True:
            self.event.wait()
            t = self.get(True)
            self.event.clear()
            t.run()

    def next (self):
        self.event.set()

    def clear (self):
        self.mutex.acquire()
        self.queue.clear()
        self.mutex.release()
        self.event.set()
