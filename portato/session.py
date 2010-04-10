# -*- coding: utf-8 -*-
#
# File: portato/session.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from future_builtins import map, filter, zip

import os
from UserDict import DictMixin

from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
from .constants import SESSION_DIR
from .helper import debug, info
from .odict import OrderedDict

NoSuchThing = (NoSectionError, NoOptionError)
sessionlist = []

class Session (object):
    """
    A small class allowing to save certain states of a program.
    This class works in a quite abstract manner, as it works with handlers, which
    define what options to use out of the config file and how to apply them to the program.
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

        self._cfg = SafeConfigParser({}, OrderedDict)
        self._handlers = []
        self._name = name if name else "MAIN"
        self._file = os.path.join(SESSION_DIR, file)

        if not (os.path.exists(SESSION_DIR) and os.path.isdir(SESSION_DIR)):
            os.mkdir(SESSION_DIR)

        oldfiles = [os.path.join(SESSION_DIR, x) for x in oldfiles]

        if not os.path.exists(self._file):
            for o in oldfiles:
                if os.path.exists(o):
                    debug("Moving old session file '%s' to '%s'." % (o, file))
                    os.rename(o,self._file)
                    break

        self._cfg.read([self._file])

        if name:
            i = _("Loading '%s' session from %s.") % (name, self._file)
        else:
            i = _("Loading session from %s.") % self._file

        info(i)

        # register
        if register: sessionlist.append(self)

        # add version check
        self.add_handler(([("version", "session")], self.check_version, lambda: self.VERSION))

    def add_handler (self, handler, default = None):
        """
        Adds a handler to this session. A handler is a three-tuple consisting of:
            - a list of (key,section) values
            - a function getting number of option arguments and applying them to the program
            - a function returning the number of option return values - getting them out of the program
        """
        (options, load_fn, save_fn) = handler
        convert = lambda x_y: (unicode(x_y[1]).upper(), unicode(x_y[0]).lower())
        options = [(self._name, unicode(x).lower()) if not hasattr(x, "__iter__") else convert(x) for x in options]
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
                except NoSuchThing: # does not exist -> ignore
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
            
            # map into list if necessary
            if not hasattr(vals, "__iter__"):
                vals = [vals]
            debug("Saving %s with values %s", options, vals)

            for value, (section, option) in zip(vals, options):
                self.set(option, unicode(value), section)
        
        with open(self._file, "w") as f:
            self._cfg.write(f)

    @classmethod
    def close (cls):
        for s in sessionlist:
            if s._name != "MAIN":
                info(_("Saving '%s' session to %s.") % (s._name, s._file))
            else:
                info(_("Saving session to %s.") % s._file)
            s.save()

    def set (self, key, value, section = None):
        if section is None: section = self._name
        section = unicode(section).upper()

        try:
            self._cfg.set(section, key, value)
        except NoSectionError:
            self._cfg.add_section(section)
            self._cfg.set(section, key, value)
    
    def get (self, key, section = None):
        if section is None: section = self._name
        section = unicode(section).upper()

        try:
            return self._cfg.get(section, key)
        except NoSuchThing:
            return None

    def get_bool (self, key, section = None):
        if section is None: section = self._name
        section = unicode(section).upper()

        try:
            return self._cfg.getboolean(section, key)
        except NoSuchThing as ValueError:
            return None
    
    def remove (self, key, section = None):
        if section is None: section = self._name
        section = unicode(section).upper()

        self._cfg.remove_option(section, key)

    def remove_section (self, section):
        section = unicode(section).upper()
        self._cfg.remove_section(section)

    def rename (self, old, new, section = None):
        if section is None: section = self._name
        section = unicode(section).upper()

        val = self.get(old, section)

        if val is not None:
            self.remove(old, section)
            self.set(new, val, section)

    def rename_section (self, old, new):
        new = unicode(new).upper()

        values = self._cfg.items(old)
        self.remove_section(old)
        for k,v in values:
            self.set(k,v,new)

    def check_version (self, vers):
        pass # do nothing atm


class SectionDict (DictMixin):
    """A class, which maps a specific section of a session to a dictionary."""

    def __init__ (self, session, section):
        self._section = unicode(section).upper()
        self._session = session

    def __getitem__ (self, name):
        item = self._session.get(name, section = self._section)

        if item is None:
            raise KeyError("%s not in section %s" % (name, self._section))
        return item

    def __setitem__ (self, name, value):
        self._session.set(name, value, section = self._section)

    def __delitem__ (self, name):
        self._session.remove(name, self._section)

    def keys (self):
        return self._session._cfg.options(self._section)

    def __contains__ (self, name):
        return self._session._cfg.has_option(self._section, name)
