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

@var APP: the application name
@type APP: string
@var VERSION: the current version
@type VERSION: string
@var HOME: shortcut to $HOME
@type HOME: string
@var SU_COMMAND: command to execute to "su"
@type SU_COMMAND: string
@var USE_SQL: whether to use the sqlite db
@type USE_SQL: boolean

@var CONFIG_DIR: The configuration directory.
@type CONFIG_DIR: string
@var CONFIG_LOCATION: L{CONFIG_DIR} plus name of the config file.
@type CONFIG_LOCATION: string

@var ICON_DIR: directory containing the icons
@type ICON_DIR: string
@var APP_ICON: the path of the application icon
@type APP_ICON: string

@var DATA_DIR: Directory which contains all shared files.
@type DATA_DIR: string
@var LOCALE_DIR: the path to the directory where the locale files (*.mo) are stored.
@type LOCALE_DIR: string
@var PLUGIN_DIR: Directory containing the plugin xmls.
@type PLUGIN_DIR: string
@var SETTINGS_DIR: Directory containing the user specific settings.
@type SETTINGS_DIR: string
@var TEMPLATE_DIR: Directory containing the UI template files.
@type TEMPLATE_DIR: string
"""
import os
from os.path import join as pjoin

# icons
ICON_DIR = "icons/"
APP_ICON = pjoin(ICON_DIR, "portato-icon.png")

# general
APP = "portato"
VERSION = "9999"
HOME = os.environ["HOME"]
SU_COMMAND = "gksu -D 'Portato'"
USE_SQL = True

# config
CONFIG_DIR = "/etc/portato/"
CONFIG_LOCATION = pjoin(CONFIG_DIR, "portato.cfg")
SESSION_DIR = pjoin(os.environ["HOME"], ".portato")

# misc dirs
DATA_DIR = "./"
LOCALE_DIR = "i18n/"
PLUGIN_DIR = pjoin(DATA_DIR, "plugins/")
SETTINGS_DIR = pjoin(HOME, "."+APP)
TEMPLATE_DIR = "portato/gui/templates/"
