# -*- coding: utf-8 -*-
#
# File: portato/helper.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net> et.al.

"""
Some nice functions used in the program.
"""
from __future__ import absolute_import, with_statement

import os, logging

debug       = logging.getLogger("portatoLogger").debug
info        = logging.getLogger("portatoLogger").info
warning     = logging.getLogger("portatoLogger").warning
error       = logging.getLogger("portatoLogger").error
critical    = logging.getLogger("portatoLogger").critical

def N_ (s):
    return s

def get_runsystem ():
     # check for sabayon first, as sabayon also has the gentoo release
    for sp in ("/etc/sabayon-release", "/etc/sabayon-edition"):
        if os.path.exists(sp):
            with open(sp) as r:
                return ("Sabayon", r.readline().strip())
    
    if os.path.exists("/etc/gentoo-release"):
            return ("Gentoo", "")

    else: return ("Unknown", "")

def paren_reduce(mystr):
    """
    Take a string and convert all paren enclosed entities into sublists, optionally
    futher splitting the list elements by spaces.
    
    This function is copied from portage.

    Example usage:
        >>> paren_reduce('foobar foo ( bar baz )')
        ['foobar', 'foo', ['bar', 'baz']]

    @param mystr: The string to reduce
    @type mystr: String
    @rtype: Array
    @return: The reduced string in an array
    """
    mylist = []
    while mystr:
        left_paren = mystr.find("(")
        has_left_paren = left_paren != -1
        right_paren = mystr.find(")")
        has_right_paren = right_paren != -1
        if not has_left_paren and not has_right_paren:
            freesec = mystr
            subsec = None
            tail = ""
        elif mystr[0] == ")":
            return [mylist,mystr[1:]]
        elif has_left_paren and not has_right_paren:
            error(_("Invalid dependency string"))
            return []
        elif has_left_paren and left_paren < right_paren:
            freesec,subsec = mystr.split("(",1)
            subsec,tail = paren_reduce(subsec)
        else:
            subsec,tail = mystr.split(")",1)
            subsec = filter(None, subsec.split(" "))
            return [mylist+subsec,tail]
        mystr = tail
        if freesec:
            mylist = mylist + filter(None, freesec.split(" "))
        if subsec is not None:
            mylist = mylist + [subsec]
    return mylist

def flatten (listOfLists):
    """Flattens the given list of lists.

    @param listOfLists: the list of lists to flatten
    @type listOfLists: list of lists
    @returns: flattend list
    @rtype: list"""

    if not isinstance(listOfLists, list):
        return [listOfLists]

    ret = []
    for r in listOfLists:
        ret.extend(flatten(r))

    return ret

def detect_desktop_environment():
    # stolen from wicd :)

    desktop_environment = 'generic'
    if os.environ.get('KDE_FULL_SESSION') == 'true':
        desktop_environment = 'kde'
    elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
        desktop_environment = 'gnome'
    #else: # no need for this part as of now
    #    try:
    #        info = commands.getoutput('xprop -root _DT_SAVE_MODE')
    #        if ' = "xfce4"' in info:
    #            desktop_environment = 'xfce'
    #    except (OSError, RuntimeError):
    #       pass
    
    return desktop_environment

