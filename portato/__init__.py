# -*- coding: utf-8 -*-
#
# File: portato/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

import gettext, locale
import sys, os
import subprocess, threading
import atexit
from optparse import OptionParser, SUPPRESS_HELP

from . import log
from .constants import LOCALE_DIR, APP, VERSION
from .su import detect_su_command
from .helper import debug, info, error

# listener-handling
__listener = None

def get_listener():
    global __listener
    if __listener is None:
        from .listener import Listener
        __listener = Listener()
    
    return __listener

def get_parser (use_ = False):
    # use_ defaults to False, if it is called from outside
    # where gettext is not yet initialized

    if not use_: _ = lambda s : s
    
    desc = "Portato - A Portage GUI."
    usage = "%prog [options] [frontend]"
    vers =  "%%prog v. %s" % VERSION

    parser = OptionParser(version = vers, prog = "Portato", description = desc, usage = usage)
    
    parser.add_option("--shm", action = "store", nargs = 3, type="long", dest = "shm",
            help = SUPPRESS_HELP)

    parser.add_option("-F", "--no-fork", "-L", action = "store_true", dest = "nofork", default = False,
            help = _("do not fork off as root") + (" (%s)" % _("-L is deprecated")))

    return parser

def start():

    # set gettext stuff
    locale.setlocale(locale.LC_ALL, '')
    gettext.install(APP, LOCALE_DIR, unicode = True)

    # start logging
    log.start(file=False)

    # run parser
    (options, args) = get_parser().parse_args()

    # close listener at exit
    atexit.register(get_listener().close)

    if options.nofork or os.getuid() == 0: # start GUI
        log.start(file = True) # start logging to file

        from .gui import run
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
        
        try:
            # set DBUS_SESSION_BUS_ADDRESS to "" to make dbus work as root ;)
            env = os.environ.copy()
            env.update(DBUS_SESSION_BUS_ADDRESS="")
            
            su = detect_su_command()
            if su:
                debug("Using '%s' as su command.", su.bin)
                cmd = su.cmd("%s --no-fork --shm %ld %ld %ld" % (sys.argv[0], mem.key, sig.key, rw.key))

                sp = subprocess.Popen(cmd, env = env)

                # wait for process to finish
                try:
                    sp.wait()
                    debug("Subprocess finished")
                except KeyboardInterrupt:
                    debug("Got KeyboardInterrupt.")

            else:
                error(_("No valid su command detected. Aborting."))
        
        finally:
            if lt.isAlive():
                debug("Listener is still running. Close it.")
                get_listener().close()
