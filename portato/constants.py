# -*- coding: utf-8 -*-
#
# File: portato/constants.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

"""
Constants used through out the program. Mainly different pathes.
These should be set during the installation.

@var VERSION: the current version
@type VERSION: string
@var CONFIG_DIR: The configuration directory.
@type CONFIG_DIR: string
@var CONFIG_LOCATION: L{CONFIG_DIR} plus name of the config file.
@type CONFIG_LOCATION: string
@var DATA_DIR: Directory which contains several data files (e.g. ui-files).
@type DATA_DIR: string
@var PLUGIN_DIR: Directory containing the plugin xmls.
@type PLUGIN_DIR: string
@var XSD_DIR: Directory containing the plugin-xml schema.
@type XSD_DIR: string
@var XSD_LOCATION: Path of the plugin schema.
@type XSD_LOCATION: string
@var ICON_DIR: directory containing the icons
@type ICON_DIR: string
@var APP_ICON: the path of the application icon
@type APP_ICON: string
@var FRONTENDS: the list of frontends which are installed
@type FRONTENDS: string[]
@var STD_FRONTEND: the frontend uses as the default, i.e. if no other one is given on the cmdline
@type STD_FRONTEND: string
"""
from os.path import join as pjoin

VERSION = "9999"

CONFIG_DIR = "/etc/portato/"
CONFIG_LOCATION = pjoin(CONFIG_DIR, "portato.cfg")

DATA_DIR = "portato/gui/templates/"
PLUGIN_DIR = "plugins/"

XSD_DIR = "./"
XSD_LOCATION = pjoin(XSD_DIR, "plugin.xsd")

ICON_DIR = "icons/"
APP_ICON = pjoin(ICON_DIR, "portato-icon.png")

FRONTENDS = ["gtk" ,"qt"]
STD_FRONTEND = "gtk"
