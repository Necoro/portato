# -*- coding: utf-8 -*-
#
# File: plugins/package_details.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import gtk
import os
from portato.gui import views

from portato.backend import system

class Detail (WidgetPlugin):
    """
    The baseclass for a detail.
    This inherits from `WidgetPlugin` and manages the basic things, like adding to the Notebook.
    """

    __author__ = "René 'Necoro' Neumann"

    _view_ = None
    _old_pkg = None
    _widget_ = None
    _widget_name_ = None
    
    def init(self):
        raise Exception, "e"
        self.add_call("update_table", self._update, type = "after")

    def widget_init (self):
        if (self._widget_ is None) or (self._widget_name_ is None):
            raise PluginLoadException, ("Has not set _widget_ or _widget_name_.")

        self.add_widget("Package Notebook", (self._widget_, self._widget_name_))

        # if the detail was updated before it was actually initialized, update it again :)
        if self._old_pkg is not None:
            self._update(self._old_pkg)

    def _update (self, pkg, page = None):
        if self._view_ is not None:
            if page is None:
                force = False
            else:
                force = page == self._view_.get_parent()

            self._view_.update(pkg, force = force)
            self._old_pkg = None
        
        else: # save
            self._old_pkg = pkg

class ScrolledDetail (Detail):
    """
    Add a ScrolledWindow.
    """

    def widget_init (self):
        self._widget_ = gtk.ScrolledWindow()
        self._widget_.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        
        if self._view_ is not None:
            self._widget_.add(self._view_)

        Detail.widget_init(self)

class ChangelogDetail (ScrolledDetail):
    __description__ = _("Shows the Changelog of a package")
    __name__ = "Detail: Changelog"
    _widget_name_ = _("Changelog")

    def widget_init (self):
        self._view_ = views.HighlightView(self.view_update, ["changelog"])
        ScrolledDetail.widget_init(self)

    def view_update (self, pkg):
        return os.path.join(pkg.get_package_path(), "ChangeLog")

class EbuildDetail (ScrolledDetail):
    __description__ = _("Shows the ebuild of a package")
    __name__ = "Detail: Ebuild"
    __dependency__ = [">=dev-python/pygtksourceview-2.4.0"]
    _widget_name_ = _("Ebuild")
    
    def widget_init(self):
        self._view_ = views.HighlightView(lambda p: p.get_ebuild_path(), ["gentoo", "sh"])
        ScrolledDetail.widget_init(self)

class FilesDetail (ScrolledDetail):
    __description__ = _("Shows the installed files of a package")
    __name__ = "Detail: Files"
    _widget_name_ = _("Files")

    def widget_init (self):
        self._view_ = views.InstalledOnlyView(self.show_files)
        ScrolledDetail.widget_init(self)

    def show_files (self, pkg):
        try:
            for f in pkg.get_files():
                yield " %s\n" % f
        except IOError, e:
            yield _("Error: %s") % e.strerror

class DependencyDetail (ScrolledDetail):
    __description__ = _("Shows the dependencies of a package")
    __name__ = "Detail: Dependency"
    _widget_name_ = _("Dependencies")

    def widget_init (self):
        self.icons = {}
        self.icons["use"] = self.window.render_icon(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
        self.icons["installed"] = self.window.render_icon(gtk.STOCK_YES, gtk.ICON_SIZE_MENU)
        self.icons["or"] = self.window.render_icon(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_MENU)
        self.icons["block"] = self.window.render_icon(gtk.STOCK_NO, gtk.ICON_SIZE_MENU)
        
        self._view_ = self.build_list()
        ScrolledDetail.widget_init(self)
    
    def sort_key (self, x):
        split = system.split_cpv(x.dep)

        if split is None: # split_cpv returns None if this is only a CP; we assume there are only valid deps
            return x.dep
        else:
            return "/".join(split[0:2])
    
    def cmp_flag (self, x, y):
        # get strings - as tuples are passed
        x = x[0]
        y = y[0]

        # remove "!"
        ret = 0
        if x[0] == "!":
            ret = 1
            x = x[1:]
        if y[0] == "!":
            ret = ret - 1 # if it is already 1, it is 0 now :)
            y = y[1:]

        # cmp -- if two flags are equal, the negated one is greater
        return cmp(x,y) or ret
    
    def get_icon (self, dep):
        if dep.satisfied:
            return self.icons["installed"]
        elif dep.dep[0] == "!":
            return self.icons["block"]
        else:
            return None
    
    def build_list (self):
        listView = views.LazyStoreView(self.fill_list)

        col = gtk.TreeViewColumn()

        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, False)
        col.add_attribute(cell, "pixbuf", 0)

        cell = gtk.CellRendererText()
        col.pack_start(cell, True)
        col.add_attribute(cell, "text", 1)

        listView.append_column(col)
        listView.set_headers_visible(False)

        return listView

    def fill_list(self, pkg):

        store = gtk.TreeStore(gtk.gdk.Pixbuf, str)
                
        def add (tree, it):
            # useflags
            flags = sorted(tree.flags.iteritems(), cmp = self.cmp_flag)
            for use, usetree in flags:
                if use[0] == "!":
                    usestring = _("If '%s' is disabled") % use[1:]
                else:
                    usestring = _("If '%s' is enabled") % use
                useit = store.append(it, [self.icons["use"], usestring])
                add(usetree, useit)
            
            # ORs
            for ortree in tree.ors:
                orit = store.append(it, [self.icons["or"], _("One of the following")])
                add(ortree, orit)

            # Sub (all of)
            for subtree in tree.subs:
                allit = store.append(it, [None, _("All of the following")])
                add(subtree, allit)

            # normal    
            ndeps = sorted(tree.deps, key = self.sort_key)
            for dep in ndeps:
                store.append(it, [self.get_icon(dep), dep.dep])
        
        try:
            deptree = pkg.get_dependencies()
        except AssertionError:
            w =  _("Can't display dependencies: This package has an unsupported dependency string.")
            error(w)
            store.append(None, [None, w])
        else:
            add(deptree, None)

        return store

# register them
register(DependencyDetail)
register(EbuildDetail)
register(FilesDetail)
register(ChangelogDetail)
