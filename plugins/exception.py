# -*- coding: utf-8 -*-
#
# File: plugins/exception.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

def throw (*args, **kwargs):
    raise Exception, "As requested, Sir!"

p = Plugin()
p.__name__ = "ExceptionThrower"
p.__author__ = "René 'Necoro' Neumann"
p.add_menu("Throw exception", throw)
register(p)
