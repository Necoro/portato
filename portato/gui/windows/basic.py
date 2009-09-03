# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/basic.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

# gtk stuff
import gtk
import gobject

from functools import wraps
import os.path

from ...constants import TEMPLATE_DIR, APP, LOCALE_DIR
from ...helper import error, debug

# for the GtkBuilder to translate correctly :)
from . import gettext
old_charset = gettext.set_gtk_gettext(APP, LOCALE_DIR)
debug("Changed from old charset '%s' to UTF-8.", old_charset)
del old_charset

class WrappedTree (object):
    __slots__ = ("klass", "tree", "get_widget", "get_ui")
    def __init__ (self, klass, tree):
        self.tree = tree
        self.klass = klass

    def __getattribute__ (self, name):
        if name in WrappedTree.__slots__:
            return object.__getattribute__(self, name)
        else:
            return getattr(self.tree, name)

    def get_widget(self, name):
        w = self.tree.get_object(name)
        if w is None:
            error("Widget '%s' could not be found in class '%s'.", name, self.klass)
        return w

    def get_ui (self, name, ui = "uimanager"):
        uiw = self.get_widget(ui)
        if uiw is None:
            return None

        if not name.startswith("ui/"):
            name = "ui/%s" % name

        w = uiw.get_widget(name)
        if w is None:
            error("UIItem '%s' of UIManager '%s' could not be found in class '%s'.", name, ui, self.klass)
        return w

class UIBuilder (object):

    def __init__ (self, connector = None):
        if not hasattr(self, "__file__"):
            self.__file__ = self.__class__.__name__

        self._builder = gtk.Builder()
        self._builder.add_from_file(os.path.join(TEMPLATE_DIR, self.__file__+".ui"))
        self._builder.set_translation_domain(APP)

        if connector is None: connector = self

        unconnected = self._builder.connect_signals(connector)

        if unconnected is not None:
            for uc in set(unconnected):
                error("Signal '%s' not connected in class '%s'.", uc, self.__class__.__name__)

        self.tree = WrappedTree(self.__class__.__name__, self._builder)

class Window (UIBuilder):
    def __init__ (self):

        UIBuilder.__init__(self)

        if not hasattr(self, "__window__"):
            self.__window__ = self.__class__.__name__

        self.window = self.tree.get_widget(self.__window__)

    @staticmethod
    def watch_cursor (func):
        """This is a decorator for functions being so time consuming, that it is appropriate to show the watch-cursor.
        @attention: this function relies on the gtk.Window-Object being stored as self.window"""
        
        @wraps(func)
        def wrapper (self, *args, **kwargs):
            ret = None
            def cb_idle():
                try:
                    ret = func(self, *args, **kwargs)
                finally:
                    self.window.window.set_cursor(None)
                return False
            
            watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
            self.window.window.set_cursor(watch)
            gobject.idle_add(cb_idle)
            return ret

        return wrapper

class AbstractDialog (Window):
    """A class all our dialogs get derived from. It sets useful default vars and automatically handles the ESC-Button."""

    def __init__ (self, parent):
        """Constructor.

        @param parent: the parent window
        @type parent: gtk.Window"""
        
        Window.__init__(self)

        # set parent
        self.window.set_transient_for(parent)
        self.parent = parent
        
        # catch the ESC-key
        self.window.connect("key-press-event", self.cb_key_pressed)

    def cb_key_pressed (self, widget, event):
        """Closes the window if ESC is pressed."""
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Escape":
            self.close()
            return True
        else:
            return False

    def close (self, *args):
        self.window.destroy()
