# -*- coding: utf-8 -*-
#
# File: portato/log.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import logging
import sys
import os

from .constants import SESSION_DIR

(S_NOT, S_STREAM_ONLY, S_BOTH) = range(3)

started = S_NOT
streamhandlers = [] # the handler printing visibile to the user

def add_handler (h):
    logging.getLogger("portatoLogger").addHandler(h)
    streamhandlers.append(h)

LOGFILE = os.path.join(SESSION_DIR, "portato.log")

class OutputFormatter (logging.Formatter):

    colors = {
            "blue"    : 34,
            "green"    : 32,
            "red"    : 31,
            "yellow": 33
            }

    def __init__(self, *args, **kwargs):
        logging.Formatter.__init__(self, *args, **kwargs)

        for key, value in self.colors.items():
            self.colors[key] = "\x1b[01;%02dm*\x1b[39;49;00m" % value

        if hasattr(sys.stderr, "fileno"):
            self.istty = os.isatty(sys.stderr.fileno())
        else:
            self.istty = False # no fileno -> safe default

    def format (self, record):
        string = logging.Formatter.format(self, record)
        color = None

        if self.istty:
            if record.levelno <= logging.DEBUG:
                color = self.colors["blue"]
            elif record.levelno <= logging.INFO:
                color = self.colors["green"]
            elif record.levelno <= logging.WARNING:
                color = self.colors["yellow"]
            else:
                color = self.colors["red"]
        else:
            color = "%s:" % record.levelname

        return "%s %s" % (color, string)

def start(file = True):
    global started

    if started == S_BOTH: return

    # logging: file
    if file:
        if not (os.path.exists(SESSION_DIR) and os.path.isdir(SESSION_DIR)):
            os.mkdir(SESSION_DIR)

        formatter = logging.Formatter("%(levelname)-8s: %(message)s (%(filename)s:%(lineno)s)")
        handler = logging.FileHandler(LOGFILE, "w")
        handler.setFormatter(formatter)
        logging.getLogger("portatoLogger").addHandler(handler)
    
    if started == S_NOT:
        logging.getLogger("portatoLogger").setLevel(logging.DEBUG)
        logging.getLogger("portatoLogger").propagate = False

    # logging: stream
    # this logger should be used
    if started == S_NOT:
        formatter = OutputFormatter("%(message)s (%(filename)s:%(lineno)s)")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        add_handler(handler)

    started = S_BOTH if file else S_STREAM_ONLY


def set_log_level (lvl):
    for h in streamhandlers:
        h.setLevel(lvl)

# embed warnings in our logging functionality
import warnings
def showwarnings(msg, cat, filename, lineno, file = None, line = None):
    msg = warnings.formatwarning(msg, cat, filename, lineno, line)

    record = logging.LogRecord("portatoLogger", logging.WARNING, filename, lineno, "Portage Warning: %s", (msg,), None)
    logging.getLogger("portatoLogger").handle(record)

warnings.showwarning = showwarnings
