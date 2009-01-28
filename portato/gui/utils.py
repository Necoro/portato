# -*- coding: utf-8 -*-
#
# File: portato/gui/utils.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

# some stuff needed
import sys
import logging
import gettext
from threading import Thread

import gtk

# some backend things
from ..backend import flags, set_system
from ..helper import debug, info, set_log_level
from ..constants import APP, LOCALE_DIR

# parser
from ..config_parser import ConfigParser

def get_color (cfg, name):
    return gtk.gdk.color_parse("#%s" % cfg.get(name, section = "COLORS"))

class GtkThread (Thread):
    def run(self):
        # for some reason, I have to install this for each thread ...
        gettext.install(APP, LOCALE_DIR, unicode = True)
        try:
            Thread.run(self)
        except SystemExit:
            raise # let normal thread handle it
        except:
            type, val, tb = sys.exc_info()
            try:
                sys.excepthook(type, val, tb, thread = self.getName())
            except TypeError:
                raise type, val, tb # let normal thread handle it
            finally:
                del type, val, tb

class Config (ConfigParser):
    
    def __init__ (self, cfgFile):
        """Constructor.

        @param cfgFile: path to config file
        @type cfgFile: string"""

        ConfigParser.__init__(self, cfgFile)
        
        # read config
        self.parse()

        # local configs
        self.local = {}

        # session configs
        self.session = {}

    def modify_flags_config (self):
        """Sets the internal config of the L{flags}-module.
        @see: L{flags.set_config()}"""

        flagCfg = {
                "usefile": self.get("useFile"),
                "usePerVersion" : self.get_boolean("usePerVersion"),
                "maskfile" : self.get("maskFile"),
                "maskPerVersion" : self.get_boolean("maskPerVersion"),
                "testingfile" : self.get("keywordFile"),
                "testingPerVersion" : self.get_boolean("keywordPerVersion")}
        flags.set_config(flagCfg)

    def modify_debug_config (self):
        if self.get_boolean("debug"):
            level = logging.DEBUG
        else:
            level = logging.INFO

        set_log_level(level)

    def modify_system_config (self):
        """Sets the system config.
        @see: L{backend.set_system()}"""
        set_system(self.get("system"))

    def modify_external_configs (self):
        """Convenience function setting all external configs."""
        self.modify_debug_config()
        self.modify_flags_config()
        self.modify_system_config()

    def set_local(self, cpv, name, val):
        """Sets some local config.

        @param cpv: the cpv describing the package for which to set this option
        @type cpv: string (cpv)
        @param name: the option's name
        @type name: string
        @param val: the value to set
        @type val: any"""
        
        if not cpv in self.local:
            self.local[cpv] = {}

        self.local[cpv].update({name:val})

    def get_local(self, cpv, name):
        """Returns something out of the local config.

        @param cpv: the cpv describing the package from which to get this option
        @type cpv: string (cpv)
        @param name: the option's name
        @type name: string
        @return: value stored for the cpv and name or None if not found
        @rtype: any"""

        if not cpv in self.local:
            return None
        if not name in self.local[cpv]:
            return None

        return self.local[cpv][name]

    def set_session (self, name, cat, val):
        self.session[(cat, name)] = val

    def get_session (self, name, cat):
        v = self.session.get((cat, name), None)

        if v == "": v = None
        return v

    def write(self):
        """Writes to the config file and modify any external configs."""
        ConfigParser.write(self)
        self.modify_external_configs()
