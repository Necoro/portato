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
from portato.gui.views import HighlightView

class Detail (WidgetPlugin):
    __author__ = "René 'Necoro' Neumann"
    _view_ = None
    old_pkg = None
    
    def init(self):
        self.add_call("update_table", self._update, type = "after")

    def widget_init (self):
        self.add_widget("Package Notebook", (self._widget_, self._widget_name_))

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
        else:
            self._old_pkg = pkg

class ScrolledDetail (Detail):

    def widget_init (self):
        self._widget_ = gtk.ScrolledWindow()
        self._widget_.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        if self._view_ is not None:
            self._widget_.add(self._view_)

        Detail.widget_init(self)
        self._widget_.show_all()

class ChangelogDetail (ScrolledDetail):
    __description__ = "Shows the Changelog of a package"
    _widget_name_ = "Changelog"

    def widget_init (self):
        self._view_ = HighlightView(self.view_update, ["changelog"])
        ScrolledDetail.widget_init(self)

    def view_update (self, pkg):
        return os.path.join(pkg.get_package_path(), "Changelog")

class EbuildDetail (ScrolledDetail):
    __description__ = "Shows the ebuild of a package"
    _widget_name_ = "Ebuild"
    
    def widget_init(self):
        self._view_ = HighlightView(lambda p: p.get_ebuild_path(), ["gentoo", "sh"])
        ScrolledDetail.widget_init(self)

register(EbuildDetail)
register(ChangelogDetail)
