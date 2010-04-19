# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/basic.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>



# gtk stuff
import gtk
import gobject

from functools import wraps
import os.path

from ...constants import TEMPLATE_DIR, APP, LOCALE_DIR
from ...helper import error, debug

# for the GtkBuilder to translate correctly :)
import ctypes
from locale import CODESET
try:
    getlib = ctypes.cdll.LoadLibrary("libgettextlib.so")
except OSError:
    error("'libgettextlib.so' cannot be loaded. Might be, that there are no translations available in the GUI.")
else:
    getlib.textdomain(APP)
    getlib.bindtextdomain(APP, LOCALE_DIR)
    getlib.bind_textdomain_codeset(APP, "UTF-8")

    # some debugging output about the current codeset used
    nll = getlib.nl_langinfo
    nll.restype = ctypes.c_char_p
    debug("Switching from '%s' to 'UTF-8'.", nll(CODESET))

    getlib.bind_textdomain_codeset(APP, "UTF-8")

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

class Window (object):

    def __init__ (self, connector = None):
        if not hasattr(self, "__file__"):
            self.__file__ = self.__class__.__name__

        # general setup
        self._builder = gtk.Builder()
        self._builder.add_from_file(os.path.join(TEMPLATE_DIR, self.__file__+".ui"))
        self._builder.set_translation_domain(APP)
        
        self.tree = WrappedTree(self.__class__.__name__, self._builder)

        if not hasattr(self, "__window__"):
            self.__window__ = self.__class__.__name__

        self.window = self.tree.get_widget(self.__window__)

        # load menu if existing
        menufile = os.path.join(TEMPLATE_DIR, self.__file__+".menu")
        if os.path.exists(menufile):
            debug("There is a menu-file for '%s'. Trying to load it.", self.__file__)
            barbox = self.tree.get_widget("menubar_box")
            if barbox is not None:
                self._add_menu(menufile, barbox)
        
        # signal connections
        if connector is None: connector = self

        unconnected = self._builder.connect_signals(connector)

        if unconnected is not None:
            for uc in set(unconnected):
                error("Signal '%s' not connected in class '%s'.", uc, self.__class__.__name__)

    def _add_menu (self, menufile, barbox):
        # add menubar
        self._builder.add_from_file(menufile)
        bar = self.tree.get_ui("menubar")
        barbox.pack_start(bar, expand = False, fill = False)

        # connect accelerators
        for ui in self._builder.get_objects():
            if isinstance(ui, gtk.UIManager):
                self.window.add_accel_group(ui.get_accel_group())

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
        
        # type hint
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

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
