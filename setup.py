#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# File: setup.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import os
import sys

from distutils.core import setup
from distutils.extension import Extension

from portato.constants import VERSION, ICON_DIR, PLUGIN_DIR, DATA_DIR, TEMPLATE_DIR, APP

from build_manpage import build_manpage

def plugin_list (*args):
    """Creates a list of correct plugin pathes out of the arguments."""
    return [("plugins/%s.py" % x) for x in args]

packages = [
            "portato",
            "portato.db",
            "portato.gui", "portato.gui.windows",
            "portato.plugins",
            "portato.backend", "portato.backend.portage"
            ]

data_files = [
        (TEMPLATE_DIR, [os.path.join("portato/gui/templates",x) for x in os.listdir("portato/gui/templates") if (x.endswith(".ui") or x.endswith(".menu"))]),
        (ICON_DIR, ["icons/portato-icon.png", "icons/better-package.svg"]),
        (DATA_DIR, ["doc/TRANSLATORS"]),
        (PLUGIN_DIR, plugin_list("gpytage", "notify", "etc_proposals", "reload_portage", "package_details"))]

cmdclass = {'build_manpage': build_manpage}

# remove useless options / they are the default
for o in (
        "eix",
        "cython", #!REMOVE
        ):
    try:
        sys.argv.remove("--enable-"+o)
    except ValueError:
        pass

# extension stuff
#!INSERT if not "--enable-cython" in sys.argv:
if "--disable-cython" in sys.argv: #!REMOVE
    sys.argv.remove("--disable-cython") #!REMOVE
    ext = "c"
else:
    #!INSERT sys.argv.remove("--enable-cython")
    from Cython.Distutils import build_ext
    cmdclass['build_ext'] = build_ext
    ext = "pyx"

ext_modules = [Extension("portato.ipc", ["portato/ipc."+ext])]

if "--disable-eix" in sys.argv:
    sys.argv.remove("--disable-eix")
else:
    ext_modules.append(Extension("portato.eix.parser", ["portato/eix/parser."+ext]))
    packages.append("portato.eix")

# do the distutils setup
setup(name=APP,
        version = VERSION,
        description = "GTK-Frontend to Portage",
        long_description =
        """%s is a frontend to the package manager of Gentoo and related distributions: Portage. It is meant to be used for browsing the tree and installing packages and their dependencies. It knows how to deal with useflags and masked packages, so it can make handling packages a lot easier.""" % APP,
        license = "GPLv2",
        url = "http://portato.origo.ethz.ch/",
        author = "René 'Necoro' Neumann",
        author_email = "necoro@necoro.net",
        packages = packages,
        data_files = data_files,
        ext_modules = ext_modules,
        cmdclass = cmdclass
        )
