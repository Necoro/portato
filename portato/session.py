# -*- coding: utf-8 -*-
#
# File: portato/session.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import os, os.path

from .config_parser import ConfigParser, SectionNotFoundException
from .constants import SESSION_DIR
from .helper import debug, info

class Session (object):
    """
    A small class allowing to save certain states of a program.
    This class works in a quite abstract manner, as it works with handlers, which
    define what options to use out of the config file and how to apply them to the program.

    Note: This class currently does not work with boolean config options. If you
    want to define boolean values, use 0 and 1. This is future proof.
    """

    # the current session format version
    VERSION = 1

    def __init__ (self, file, name="", oldfiles = []):
        """
        Initialize a session with a certain file inside L{SESSION_DIR}.

        @param file: the file in L{SESSION_DIR}, where the options will be saved.
        @param oldfiles: old file names for the same file
        @param name: short name describing the type of session
        """

        self._cfg = None
        self._handlers = []
        self._name = name if name else "MAIN"

        if not (os.path.exists(SESSION_DIR) and os.path.isdir(SESSION_DIR)):
            os.mkdir(SESSION_DIR)

        file = os.path.join(SESSION_DIR, file)
        oldfiles = [os.path.join(SESSION_DIR, x) for x in oldfiles]

        if not os.path.exists(file):
            for o in oldfiles:
                if os.path.exists(o):
                    debug("Moving old session file '%s' to '%s'." % (o, file))
                    os.rename(o,file)
                    break

        self._cfg = ConfigParser(file)

        if name:
            i = _("Loading '%s' session from '%s'.") % (name, self._cfg.file)
        else:
            i = _("Loading session from '%s'.") % self._cfg.file

        info(i)

        try:
            self._cfg.parse()
        except IOError, e:
            if e.errno == 2: pass
            else: raise

        # add version check
        self.add_handler(([("version", "session")], self.check_version, lambda: self.VERSION))

    def add_handler (self, (options, load_fn, save_fn), default = None):
        """
        Adds a handler to this session. A handler is a three-tuple consisting of:
            - a list of (key,section) values
            - a function getting number of option arguments and applying them to the program
            - a function returning the number of option return values - getting them out of the program
        """
        self._handlers.append((options, load_fn, save_fn, default))

    def load (self, defaults_only = False):
        """
        Loads and applies all values of the session.
        """
        
        def ldefault (options, lfn, default):
            if not default: return
            debug("Loading %s with defaults %s.", options, default)
            lfn(*default)

        for options, lfn, sfn, default in self._handlers:
            if defaults_only:
                ldefault(options, lfn, default)
            else:
                try:
                    loaded = [self._cfg.get(*x) for x in options]
                except KeyError: # does not exist -> ignore
                    debug("No values for %s.", options)
                    ldefault(options, lfn, default)
                else:
                    debug("Loading %s with values %s.", options, loaded)
                    lfn(*loaded)

    def save (self):
        """
        Saves all options into the file.
        """

        for options, lfn, sfn, default in self._handlers:
            vals = sfn()
            
            # map into list if necessairy
            if not hasattr(vals, "__iter__"):
                vals = [vals]
            debug("Saving %s with values %s", options, vals)

            for value, (option, section) in zip(vals, options):
                self.set(option, str(value), section)
        
        self._cfg.write()

    def set (self, key, value, section = ""):
        if not section: section = self._name

        try:
            self._cfg.add(key, value, section, with_blankline = False)
        except SectionNotFoundException:
            self._cfg.add_section(section)
            self._cfg.add(key, value, section, with_blankline = False)
    
    def get (self, key, section = ""):
        if not section: section = self._name

        try:
            return self._cfg.get(key, section)
        except KeyError:
            return None
    
    def get_boolean (self, key, section = ""):
        if not section: section = self._name

        try:
            return self._cfg.get_boolean(key, section)
        except KeyError:
            return None

    def check_version (self, vers):
        pass # do nothing atm
