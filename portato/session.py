# -*- coding: utf-8 -*-
#
# File: portato/session.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import os
from UserDict import DictMixin

from .config_parser import ConfigParser, SectionNotFoundException
from .constants import SESSION_DIR
from .helper import debug, info

sessionlist = []

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

    def __init__ (self, file, name="", oldfiles = [], register = True):
        """
        Initialize a session with a certain file inside L{SESSION_DIR}.

        @param file: the file in L{SESSION_DIR}, where the options will be saved.
        @param oldfiles: old file names for the same file
        @param name: short name describing the type of session
        @param register: register in the global sessionlist, which is closed at the end
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
            i = _("Loading '%s' session from %s.") % (name, self._cfg.file)
        else:
            i = _("Loading session from %s.") % self._cfg.file

        info(i)

        try:
            self._cfg.parse()
        except IOError, e:
            if e.errno == 2: pass
            else: raise

        # register
        if register: sessionlist.append(self)

        # add version check
        self.add_handler(([("version", "session")], self.check_version, lambda: self.VERSION))

    def add_handler (self, (options, load_fn, save_fn), default = None):
        """
        Adds a handler to this session. A handler is a three-tuple consisting of:
            - a list of (key,section) values
            - a function getting number of option arguments and applying them to the program
            - a function returning the number of option return values - getting them out of the program
        """

        options = map(lambda x: (x, self._name) if not hasattr(x, "__iter__") else x, options)
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

    @classmethod
    def close (cls):
        for s in sessionlist:
            if s._name != "MAIN":
                info(_("Saving '%s' session to %s.") % (s._name, s._cfg.file))
            else:
                info(_("Saving session to %s.") % s._cfg.file)
            s.save()

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

    def remove (self, key, section = ""):
        if not section: section = self._name

        section = section.upper()
        key = key.lower()

        val = self._cfg._access(key, section)
        del self._cfg.cache[val.line]

        self._cfg.write()

    def remove_section (self, section):
        section = section.upper()

        sline = self._cfg.sections[section]

        try:
            mline = max(v.line for v in self._cfg.vars[section].itervalues())
        except ValueError: # nothing in the section
            mline = sline
        
        sline = max(sline - 1, 0) # remove blank line too - but only if there is one ;)

        del self._cfg.cache[sline:mline+1]
        self._cfg.write()

    def rename (self, old, new, section = ""):
        if not section: section = self._name
        
        val = self.get(old, section)
        self.remove(old, section)
        self._cfg.add(new, val, section, with_blankline = False)

    def rename_section (self, old, new):
        old = old.upper()
        line = self._cfg.sections[old]
        self._cfg.cache[line] = "[%s]\n" % new.upper()
        self._cfg.write()

    def check_version (self, vers):
        pass # do nothing atm

class SectionDict (DictMixin):
    """A class, which maps a specific section of a session to a dictionary."""

    def __init__ (self, session, section):
        self._section = section.upper()
        self._session = session

    def __getitem__ (self, name):
        item = self._session.get(name, section = self._section)

        if item is None:
            raise KeyError, "%s not in section %s" % (name, self._section)
        return item

    def __setitem__ (self, name, value):
        self._session.set(name, value, section = self._section)

    def __delitem__ (self, name):
        self._session.remove(name, self._section)

    def keys (self):
        return self._session._cfg.vars[self._section].keys()

    def __contains__ (self, name):
        return self._session.get(name, self._section) is not None
