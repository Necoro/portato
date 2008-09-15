#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# File: portato.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import with_statement, absolute_import

import sys, os
import subprocess, threading
import atexit
import gettext, locale
from optparse import OptionParser, SUPPRESS_HELP

from portato import get_listener, log
from portato.helper import debug, info
from portato.constants import VERSION, LOCALE_DIR, APP, SU_COMMAND

def main ():
    # set gettext stuff
    locale.setlocale(locale.LC_ALL, '')
    gettext.install(APP, LOCALE_DIR, unicode = True)

    # build the parser
    desc = "Portato - A Portage GUI."
    usage = "%prog [options] [frontend]"
    vers =  "%%prog v. %s" % VERSION

    parser = OptionParser(version = vers, prog = "Portato", description = desc, usage = usage)
    
    parser.add_option("--shm", action = "store", nargs = 3, type="long", dest = "shm",
            help = SUPPRESS_HELP)

    parser.add_option("-F", "--no-fork", "-L", action = "store_true", dest = "nofork", default = False, 
            help = _("do not fork off as root") + (" (%s)" % _("-L is deprecated")))

    # run parser
    (options, args) = parser.parse_args()

    # close listener at exit
    atexit.register(get_listener().close)

    if options.nofork or os.getuid() == 0: # start GUI
        log.start(file = True) # start logging to file

        from portato.gui import run
        info("%s v. %s", _("Starting Portato"), VERSION)
        
        if options.shm:
            get_listener().set_send(*options.shm)
        else:
            get_listener().set_send()
        
        try:
            run()
        except KeyboardInterrupt:
            debug("Got KeyboardInterrupt.")
        
    else: # start us again in root modus and launch listener
        
        import shm_wrapper as shm

        mem = shm.create_memory(1024, permissions=0600)
        sig = shm.create_semaphore(InitialValue = 0, permissions = 0600)
        rw = shm.create_semaphore(InitialValue = 1, permissions = 0600)
        
        # start listener
        lt = threading.Thread(target=get_listener().set_recv, args = (mem, sig, rw))
        lt.setDaemon(False)
        lt.start()
        
        # set DBUS_SESSION_BUS_ADDRESS to "" to make dbus work as root ;)
        env = os.environ.copy()
        env.update(DBUS_SESSION_BUS_ADDRESS="")
        cmd = SU_COMMAND.split()
        
        sp = subprocess.Popen(cmd+["%s --no-fork --shm %ld %ld %ld" % (sys.argv[0], mem.key, sig.key, rw.key)], env = env)

        # wait for process to finish
        try:
            sp.wait()
            debug("Subprocess finished")
        except KeyboardInterrupt:
            debug("Got KeyboardInterrupt.")

        if lt.isAlive():
            debug("Listener is still running. Close it.")
            get_listener().close()

if __name__ == "__main__":
    main()
