# -*- coding: utf-8 -*-
#
# File: portato/gui/windows/main.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

# gtk stuff
import gtk
import gobject
import vte

# other
import os
import itertools as itt
import operator as op
from collections import defaultdict

# our backend stuff
from ...backend import flags, system # must be the first to avoid circular deps
from ... import get_listener
from ...helper import debug, warning, error, info
from ...session import Session
from ...db import Database
from ...db.database import UnsupportedSearchTypeError
from ...constants import CONFIG_LOCATION, VERSION, APP_ICON, ICON_DIR
from ...backend.exceptions import PackageNotFoundException, BlockedException, VersionsNotFoundException

# plugin stuff
from ... import plugin
from .. import slots

# more GUI stuff
from .. import dialogs
from ..utils import Config, GtkThread, GtkTree, get_color
from ..queue import EmergeQueue
from ..session import SESSION_VERSION, SessionException, OldSessionException, NewSessionException
from ..views import LogView, LazyStoreView
from ..exceptions import PreReqError

# even more GUI stuff
from .basic import Window
from .about import AboutWindow
from .plugin import PluginWindow
from .preference import PreferenceWindow
from .search import SearchWindow
from .pkglist import UpdateWindow, WorldListWindow

class PackageTable:
    """A window with data about a specfic package."""

    def __init__ (self, main):
        """Build up window contents.
        
        @param main: the main window
        @type main: MainWindow"""

        self.main = main
        self.tree = main.tree
        self.window = main.window
        
        # all the package data is in this one VB
        self.vb = self.tree.get_widget("packageVB")

        # the notebook
        self.notebook = self.tree.get_widget("packageNotebook")
        
        # chechboxes
        self.installedCheck = self.tree.get_widget("installedCheck")
        self.maskedCheck = self.tree.get_widget("maskedCheck")
        self.testingCheck = self.tree.get_widget("testingCheck")
        self.maskedLabel = self.tree.get_widget("maskedLabel")

        # labels
        self.main.set_color(get_color(self.main.cfg, "packagetable"))
        
        self.nameLabel = self.tree.get_widget("nameLabel")
        self.descLabel = self.tree.get_widget("descLabel")
        self.overlayLabel = self.tree.get_widget("overlayLabel")
        self.overlayLL = self.tree.get_widget("overlayLabelLabel")
        self.licenseLabel = self.tree.get_widget("licenseLabel")
        self.linkBox = self.tree.get_widget("linkBox")
        self.notInSysLabel = self.tree.get_widget("notInSysLabel")
        self.missingLabel = self.tree.get_widget("missingLabel")
        self.useFlagsLabel = self.tree.get_widget("useFlagsLabel")
        self.useFlagsLL = self.tree.get_widget("useFlagsLabelLabel")
        
        # buttons
        self.emergeBtn = self.tree.get_widget("pkgEmergeBtn")
        self.unmergeBtn = self.tree.get_widget("pkgUnmergeBtn")
        self.revertBtn = self.tree.get_widget("pkgRevertBtn")
        
        # useList
        self.useList = self.tree.get_widget("useListScroll").get_child()


    def update (self, pkg, queue = None, doEmerge = True, instantChange = False, type = None):
        """Updates the table to show the contents for the package.
        
        @param pkg: the selected package
        @type pkg: Package
        @param queue: emerge-queue (if None the emerge-buttons are disabled)
        @type queue: EmergeQueue
        @param doEmerge: if False, the emerge buttons are disabled
        @type doEmerge: boolean
        @param instantChange: if True the changed keywords are updated instantly
        @type instantChange: boolean
        @param type: the type of the queue this package is in; if None there is no queue :)
        @type type: string"""
        
        self.pkg = pkg
        self.queue = queue
        self.doEmerge = doEmerge
        self.instantChange = instantChange
        self.type = type

        if not self.queue or not self.doEmerge:
            self.emergeBtn.set_sensitive(False)
            self.unmergeBtn.set_sensitive(False)
        
        # current status
        self._update_table()
        self.vb.show_all()

    def hide (self):
        self.vb.hide_all()

    def set_labels (self):
        pkg = self.pkg
        
        # name
        self.nameLabel.set_markup("<b>%s</b>" % pkg.get_cpv())
        
        # description
        desc = pkg.get_package_settings("DESCRIPTION") or _("<no description>")
        self.descLabel.set_label(desc)

        # overlay
        if pkg.is_in_overlay():
            self.overlayLabel.set_label(pkg.get_overlay_path())
            self.overlayLabel.show()
            self.overlayLL.show()
        else:
            self.overlayLabel.hide()
            self.overlayLL.hide()

        # license
        self.licenseLabel.set_label(pkg.get_package_settings("LICENSE"))

        # link
        for c in self.linkBox.get_children():
            self.linkBox.remove(c)
        
        text = pkg.get_package_settings("HOMEPAGE")
        texts = text.split()
        ftexts = []

        for count, t in enumerate(texts):
            if not t.startswith(("http", "ftp")):
                if count == 0:
                    error(_("The first homepage part does not start with 'http' or 'ftp'."))
                    ftexts.append(t)
                    continue
                else:
                    info(_("Blank inside homepage."))
                    ftexts[-1] += " %s" % t
            else:
                ftexts.append(t)

        for t in ftexts:
            link = gtk.LinkButton(uri = t, label = t)
            link.set_alignment(0.0, 0.5)
            link.set_border_width(0)
            self.linkBox.add(link)

        # useflags
        flaglist = list(itt.ifilterfalse(pkg.use_expanded, pkg.get_iuse_flags()))
        flaglist.sort()
        flagstr = ", ".join(flaglist)

        if flagstr:
            self.useFlagsLL.show()
            self.useFlagsLabel.show()
            self.useFlagsLabel.set_label(flagstr)
        else:
            self.useFlagsLL.hide()
            self.useFlagsLabel.hide()

    def _update_keywords (self, emerge, update = False):
        if emerge:
            type = "install" if not self.type else self.type
            try:
                try:
                    self.queue.append(self.pkg.get_cpv(), type = type, update = update)
                except PackageNotFoundException, e:
                    if dialogs.unmask_dialog(e[0]) == gtk.RESPONSE_YES:
                        self.queue.append(self.pkg.get_cpv(), type = type, unmask = True, update = update)
            except BlockedException, e:
                dialogs.blocked_dialog(e[0], e[1])
        else:
            try:
                self.queue.append(self.pkg.get_cpv(), type = "uninstall")
            except PackageNotFoundException, e:
                error(_("Package could not be found: %s"), e[0])
                #masked_dialog(e[0])

    def _update_table (self, *args):
        pkg = self.pkg

        # update useList if needed
        nb_page = self.notebook.get_nth_page(self.notebook.get_current_page())
        self.useList.update(pkg, force = nb_page == self.useList.get_parent())
        
        @plugin.hook("update_table", pkg = pkg, page = self.notebook.get_nth_page(self.notebook.get_current_page()))
        def _update():
            # set the labels
            self.set_labels()

            #
            # rebuild the buttons and checkboxes in all the different manners which are possible
            #
            if (not pkg.is_in_system()) or pkg.is_missing_keyword():
                if not pkg.is_in_system():
                    self.missingLabel.hide()
                    self.notInSysLabel.show()
                else: # missing keyword
                    self.missingLabel.show()
                    self.notInSysLabel.hide()
                
                self.installedCheck.hide()
                self.maskedCheck.hide()
                self.maskedLabel.set_label("") # this is needed for some unknown reason
                self.maskedLabel.hide()
                self.testingCheck.hide()
                self.emergeBtn.set_sensitive(False)
            else: # normal package
                self.missingLabel.hide()
                self.notInSysLabel.hide()
                self.installedCheck.show()
                self.maskedCheck.show()
                self.maskedLabel.show()
                self.testingCheck.show()
                if self.doEmerge:
                    self.emergeBtn.set_sensitive(True)
                self.installedCheck.set_active(pkg.is_installed())
                
                reason = pkg.get_masking_reason() or " "
                if pkg.is_masked(use_changed = False) and not pkg.is_masked(use_changed = True):
                    self.maskedCheck.set_label("<i>(%s)</i>" % _("Masked"))
                    self.maskedCheck.get_child().set_use_markup(True)
                else:
                    self.maskedCheck.set_label(_("Masked"))
                
                if pkg.is_locally_masked():
                    self.maskedCheck.set_label("<b>%s</b>" % _("Masked"))
                    self.maskedCheck.get_child().set_use_markup(True)
                    self.maskedCheck.set_active(True)
                    reason = _("Masked by user")
                else:
                    self.maskedCheck.set_active(pkg.is_masked(use_changed = False))
                
                self.maskedLabel.set_label(reason)
                
                if pkg.is_testing(use_keywords = False) and not pkg.is_testing(use_keywords = True):
                    self.testingCheck.set_label("<i>(%s)</i>" % _("Testing"))
                    self.testingCheck.get_child().set_use_markup(True)
                else:
                    self.testingCheck.set_label(_("Testing"))
                
                self.testingCheck.set_active(pkg.is_testing(use_keywords = False))

            if self.doEmerge:
                # set emerge-button-label
                if not pkg.is_installed():
                    self.unmergeBtn.set_sensitive(False)
                else:
                    self.unmergeBtn.set_sensitive(True)
            
            self.vb.show_all()

        _update()
        return True

    def cb_button_pressed (self, b, event):
        """Callback for pressed checkboxes. Just quits the event-loop - no redrawing."""
        if not isinstance(b, gtk.CellRendererToggle):
            b.emit_stop_by_name("button-press-event")
        return True

    def cb_package_revert_clicked (self, button):
        """Callback for pressed revert-button."""
        self.pkg.remove_new_use_flags()
        self.pkg.remove_new_masked()
        self.pkg.remove_new_testing()
        self._update_table()
        if self.instantChange:
            self._update_keywords(True, update = True)
        return True

    def cb_package_emerge_clicked (self, button):
        """Callback for pressed emerge-button. Adds the package to the EmergeQueue."""
        self._update_keywords(True)
        self.main.sysNotebook.set_current_page(self.main.QUEUE_PAGE)
        return True

    def cb_package_unmerge_clicked (self, button):
        """Callback for pressed unmerge-button clicked. Adds the package to the UnmergeQueue."""
        self._update_keywords(False)
        self.main.sysNotebook.set_current_page(self.main.QUEUE_PAGE)
        return True

    def cb_testing_toggled (self, button):
        """Callback for toggled testing-checkbox."""
        status = button.get_active()

        # end of recursion :)
        if self.pkg.is_testing(use_keywords = False) == status:
            return False

        # if the package is not testing - don't allow to set it as such
        if not self.pkg.is_testing(use_keywords = False):
            button.set_active(False)
            return True

        # re-set to testing status
        if not self.pkg.is_testing(use_keywords = True):
            self.pkg.set_testing(False)
            button.set_label(_("Testing"))
            button.set_active(True)
        else: # disable testing
            self.pkg.set_testing(True)
            button.set_label("<i>(%s)</i>" % _("Testing"))
            button.get_child().set_use_markup(True)
            button.set_active(True)

        if self.instantChange:
            self._update_keywords(True, update = True)
        
        return True

    def cb_masked_toggled (self, button):
        """Callback for toggled masking-checkbox."""
        status = button.get_active()
        pkg = self.pkg

        if pkg.is_masked(use_changed = False) == status and not pkg.is_locally_masked():
            return False

        if pkg.is_locally_masked() and status:
            return False
    
        if not pkg.is_masked(use_changed = True):
            pkg.set_masked(True)
            if pkg.is_locally_masked():
                button.set_label("<b>%s</b>" % _("Masked"))
                button.get_child().set_use_markup(True)
                self.maskedLabel.set_label(_("Masked by user"))
            else:
                button.set_label(_("Masked"))

            button.set_active(True)
        else:
            locally = pkg.is_locally_masked()
            pkg.set_masked(False)
            if pkg.is_masked(use_changed=False) and not locally:
                button.set_label("<i>(%s)</i>" % _("Masked"))
                button.get_child().set_use_markup(True)
                button.set_active(True)
            else:
                button.set_label(_("Masked"))
                self.maskedLabel.set_label("")
        
        if self.instantChange:
            self._update_keywords(True, update = True)
        
        return True

    def cb_use_flag_toggled (self, cell, path):
        """Callback for a toggled use-flag button."""

        store = self.useList.get_model()

        flag = store[path][2]
        pkg = self.pkg
        
        store[path][0] = not store[path][0]
        prefix = ""
        if not store[path][0]:
            prefix = "-"
        
        pkg.set_use_flag(prefix+flag)
        if self.instantChange:
            self._update_keywords(True, update = True)
    
        return True

class MainWindow (Window):
    """
    Application main window.
    """

    # NOTEBOOK PAGE CONSTANTS
    (
            QUEUE_PAGE,
            CONSOLE_PAGE,
            LOG_PAGE
    ) = range(3)

    def __init__ (self, splash = None):
        """
        Build up window.

        @param splash: the splash screen =)
        @type splash: SplashScreen
        """

        self.check_prereqs()

        if splash is None:
            splash = lambda x: True
        
        # the title
        self.main_title = "Portato (%s)" % VERSION

        # main window stuff
        Window.__init__(self)
        self.window.set_title(self.main_title)
        self.window.set_geometry_hints (self.window, max_height = gtk.gdk.screen_height(), max_width = gtk.gdk.screen_width())
        
        # app icon
        gtk.window_set_default_icon_from_file(APP_ICON)
        
        # booleans
        self.doUpdate = False
        self.showAll = True # show only installed or all packages?
        self.__searchChanged = False

        # our own icon factory
        fac = gtk.IconFactory()
        iSet = gtk.IconSet()
        iSource = gtk.IconSource()
        iSource.set_filename(os.path.abspath(os.path.join(ICON_DIR, "better-package.svg")))
        iSet.add_source(iSource)
        fac.add("portato-better-pkg", iSet)
        fac.add_default()

        # icons
        self.icons = {}
        self.icons["installed"] = self.window.render_icon(gtk.STOCK_YES, gtk.ICON_SIZE_MENU)
        self.icons["or"] = self.window.render_icon(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_MENU)
        self.icons["better"] = self.window.render_icon("portato-better-pkg", gtk.ICON_SIZE_MENU)
        
        # get the logging window as soon as possible
        self.logView = LogView(self.tree.get_widget("logView"))
        
        # config
        splash(_("Loading Config"))
        try:
            self.cfg = Config(CONFIG_LOCATION)
        except IOError, e:
            dialogs.io_ex_dialog(e)
            raise

        self.cfg.modify_external_configs()
        self.set_uri_hook(self.cfg.get("browserCmd", section = "GUI"))
        gtk.about_dialog_set_url_hook(lambda *args: True) # dummy - if not set link is not set as link; if link is clicked the normal uuri_hook is called too - thus do not call browser here

        # package db
        splash(_("Creating Database"))
        self.db = Database(self.cfg.get("type", section = "DATABASE"))
        
        # set plugins and plugin-menu
        splash(_("Loading Plugins"))

        optionsHB = self.tree.get_widget("optionsHB")
        slots.WidgetSlot(gtk.CheckButton, "Emerge Options", add = lambda w: optionsHB.pack_end(w.widget))

        slots.PluginMenuSlot(self.tree)
        plugin.load_plugins()

        splash(_("Building frontend"))
        # set paned position
        self.vpaned = self.tree.get_widget("vpaned")
        self.vpaned.set_position(int(self.window.get_size()[1]/2))
        self.hpaned = self.tree.get_widget("hpaned")
        self.hpaned.set_position(int(self.window.get_size()[0]/1.5))

        # lists
        self.selCatName = ""
        self.selCP = ""
        self.selCPV = ""
        self.sortPkgListByName = True
        self.catList = self.tree.get_widget("catList")
        self.pkgList = self.tree.get_widget("pkgList")
        self.versionList = self.tree.get_widget("versionList")
        self.build_cat_list()
        self.build_pkg_list()
        self.build_version_list()

        # search entry
        self.searchEntry = self.tree.get_widget("searchEntry")

        # queue list
        self.queueOneshot = self.tree.get_widget("oneshotCB")
        self.queueOneshotHandler = self.queueOneshot.connect("toggled", self.cb_oneshot_clicked)
        self.queueList = self.tree.get_widget("queueList")
        self.build_queue_list()

        # the terminal
        self.console = vte.Terminal()
        self.termHB = self.tree.get_widget("termHB")
        self.build_terminal()
        
        # notebooks
        self.sysNotebook = self.tree.get_widget("systemNotebook")
        self.pkgNotebook = self.tree.get_widget("packageNotebook")
        self.set_notebook_tabpos(map(PreferenceWindow.tabpos.get, map(int, (self.cfg.get("packageTabPos", "GUI"), self.cfg.get("systemTabPos", "GUI")))))
        slots.NotebookSlot(self.pkgNotebook, gtk.Widget, "Package Notebook")
        
        # the useScroll
        useScroll = self.tree.get_widget("useListScroll")
        useScroll.add(self.build_use_list())
        
        # table
        self.packageTable = PackageTable(self)

        # popups
        self.consolePopup = self.tree.get_ui("consolePopup")
        self.trayPopup = self.tree.get_ui("systrayPopup")

        # pause menu items
        self.emergePaused = False

        # systray
        if self.cfg.get_boolean("showSystray", "GUI"):
            self.tray = gtk.status_icon_new_from_file(APP_ICON)
            self.tray.connect("activate", self.cb_systray_activated)
            self.tray.connect("popup-menu", lambda icon, btn, time: self.trayPopup.popup(None, None, None, btn, time))
        else:
            self.tray = None

        # set emerge queue
        self.queueTree = GtkTree(self.queueList.get_model())
        self.queue = EmergeQueue(console = self.console, tree = self.queueTree, db = self.db, title_update = self.title_update, threadClass = GtkThread)
        
        # session
        splash(_("Restoring Session"))
        try:
            try:
                self.load_session()
            except OldSessionException, e:
                self.load_session(e)
        except SessionException, e:
            warning(str(e))
            self.load_session(defaults_only = True) # last ressort

        splash(_("Loading Plugin Widgets"))
        plugin.load_plugin_widgets(self.window)
        
        splash(_("Finishing startup"))
        
        # depends on session
        self.typeCombo = self.tree.get_widget("typeCombo")
        self.build_type_combo()
        
        self.window.show_all()
    
    def show_package (self, pkg = None, cpv = None, cp = None, version = None, **kwargs):
        p = None

        if pkg:
            p = pkg
        elif cpv:
            p = system.find_packages("="+cpv, masked = True)[0]
        elif cp:
            if version:
                p = system.find_packages("=%s-%s" % (cp, version), masked = True)[0]
            
            else:
                best = system.find_best_match(cp)
                if best:
                    p = best
                else:
                    p = system.find_packages(cp, masked = True)[0]
        
        self.packageTable.update(p, **kwargs)

    def build_terminal (self):
        """
        Builds the terminal.
        """
        
        self.console.set_scrollback_lines(int(self.cfg.get("scrollbacklines", "GUI")))
        self.console.set_scroll_on_output(True)
        self.console.set_font_from_string(self.cfg.get("consolefont", "GUI"))
        self.console.connect("button-press-event", self.cb_right_click)
        self.termHB.pack_start(self.console, True, True)
        
        # add scrollbar
        termScroll = gtk.VScrollbar(self.console.get_adjustment())
        self.termHB.pack_start(termScroll, False)

    def build_queue_list (self):
        """
        Builds the queue list.
        """

        store = gtk.TreeStore(str,str,bool)
        
        self.queueList.set_model(store)
        
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Queue"), cell, markup = 0)
        self.queueList.append_column(col)
        
        col = gtk.TreeViewColumn(_("Options"), cell, markup = 1)
        self.queueList.append_column(col)

        self.queueList.get_selection().connect("changed", self.cb_queue_list_selection)

    def build_cat_list (self):
        """
        Builds the category list.
        """
        
        store = gtk.TreeStore(str)

        self.fill_cat_store(store)

        self.catList.set_model(store)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Categories"), cell, text = 0)
        self.catList.append_column(col)

        self.catList.get_selection().connect("changed", self.cb_cat_list_selection)

    def fill_cat_store (self, store = None):
        """
        Fills the category store with data.
    
        @param store: the store to fill
        @type store: gtk.ListStore
        """

        if store is None:
            store = self.catList.get_model()
        
        store.clear()

        cats = self.db.get_categories(installed = not self.showAll)

        if not self.cfg.get_boolean("collapseCats", "GUI"):
            for p in cats:
                store.append(None, [p])
        else:
            splitCats = defaultdict(list)
            for c in cats:
                try:
                    pre, post = c.split("-", 1)
                except ValueError: # no "-" in cat name -- do not split
                    debug("Category '%s' can't be split up. Should be no harm.", c)
                    splitCats["not-split"].append(c)
                else:
                    splitCats[pre].append(post)

            for sc in splitCats:
                if sc == "not-split":
                    it = None # append not splitted stuff to root
                else:
                    it = store.append(None, [sc])
                for cat in splitCats[sc]:
                    store.append(it, [cat])
        
        # sort them alphabetically
        store.set_sort_column_id(0, gtk.SORT_ASCENDING)

    def build_pkg_list (self, name = None):
        """
        Builds the package list.
        
        @param name: name of the selected catetegory
        @type name: string
        """
        
        store = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        self.fill_pkg_store(store, name)
        
        # build view
        self.pkgList.set_model(store)
        
        col = gtk.TreeViewColumn(_("Packages"))
        col.set_clickable(True)
        col.connect("clicked", self.cb_pkg_list_header_clicked)

        # adding the pixbuf
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, False)
        col.add_attribute(cell, "pixbuf", 0)
        
        # adding the package name
        cell = gtk.CellRendererText()
        col.pack_start(cell, True)
        col.add_attribute(cell, "text", 1)
        
        self.pkgList.append_column(col)

        self.pkgList.get_selection().connect("changed", self.cb_pkg_list_selection)

    def fill_pkg_store (self, store = None, name = None):
        """
        Fills a given ListStore with the packages in a category.
        
        @param store: the store to fill
        @type store: gtk.ListStore
        @param name: the name of the category
        @type name: string
        """
        
        if store is None:
            store = self.pkgList.get_model()
        store.clear()

        if name:
            for pkg in self.db.get_cat(name, self.sortPkgListByName):
                if pkg.disabled:
                    warning(_("Package '%s/%s' is disabled."), pkg.cat, pkg.pkg)
                    continue

                if pkg.inst:
                    icon = self.icons["installed"]
                elif not self.showAll:
                    continue # ignore not installed packages
                else:
                    icon = None
                store.append([icon, pkg.pkg, pkg.cat])

    def build_version_list (self):
        store = gtk.ListStore(gtk.gdk.Pixbuf, str, str)

        # build view
        self.versionList.set_model(store)
        
        col = gtk.TreeViewColumn(_("Versions"))
        col.set_property("expand", True)
        
        self.slotcol = gtk.TreeViewColumn(_("Slot"))
        self.slotcol.set_property("expand", True)

        # adding the pixbuf
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, False)
        col.add_attribute(cell, "pixbuf", 0)

        # adding the package name
        cell = gtk.CellRendererText()
        col.pack_start(cell, True)
        col.add_attribute(cell, "text", 1)

        # adding the slot
        cell = gtk.CellRendererText()
        self.slotcol.pack_start(cell, True)
        self.slotcol.add_attribute(cell, "text", 2)

        self.versionList.append_column(col)
        self.versionList.append_column(self.slotcol)

        self.versionList.get_selection().connect("changed", self.cb_vers_list_selection)

    def fill_version_list (self, cp, version = None):
        
        store = self.versionList.get_model()
        store.clear()

        # this is here for performance reasons
        # to not query the package with info, we do not need
        if self.cfg.get_boolean("showSlots", "GUI"):
            def get_slot(pkg):
                return pkg.get_package_settings("SLOT")
            
            self.slotcol.set_visible(True)
        
        else:
            def get_slot(*args):
                return ""
            
            self.slotcol.set_visible(False)

        packages = system.sort_package_list(system.find_packages(cp, masked=True))
        if not packages:
            raise VersionsNotFoundException(cp)
        
        best = system.find_best_match(cp)

        # append versions
        for vers, inst, slot in ((x.get_version(), x.is_installed(), get_slot(x)) for x in packages):
            if inst:
                icon = self.icons["installed"]
            elif best is not None and vers == best.get_version():
                icon = self.icons["better"]
            else:
                icon = None
                
            store.append([icon, vers, slot])

        pos = ((0,)) # default
        
        # activate the first one
        try:
            best_version = ""
            if version:
                best_version = version
            else:
                best_version = system.find_best_match(packages[0].get_cp()).get_version()
            for i, p in enumerate(packages):
                if p.get_version() == best_version:
                    pos = (i,)
                    break
        except AttributeError: # no package found
            pass

        self.versionList.get_selection().select_path(pos)
        self.versionList.scroll_to_cell(pos)

    def build_use_list (self):
        """Builds the useList."""

        useList = LazyStoreView(self.fill_use_list)

        # build view
        cell = gtk.CellRendererText()
        iCell = gtk.CellRendererToggle()
        iCell.set_property("activatable", False)
        tCell = gtk.CellRendererToggle()
        tCell.set_property("activatable", True)
        tCell.connect("toggled", self.cb_use_flag_toggled)
        useList.append_column(gtk.TreeViewColumn(_("Enabled"), tCell, active = 0, activatable = 4))
        useList.append_column(gtk.TreeViewColumn(_("Installed"), iCell, active = 1))
        useList.append_column(gtk.TreeViewColumn(_("Flag"), cell, text = 2))
        useList.append_column(gtk.TreeViewColumn(_("Description"), cell, markup = 3))

        useList.set_search_column(2)
        useList.set_enable_tree_lines(True)

        return useList
    
    def fill_use_list(self, pkg):
        store = gtk.TreeStore(bool, bool, str, str, bool)

        pkg_flags = pkg.get_iuse_flags()
        pkg_flags.sort()
    
        actual_exp = None
        actual_exp_it = None

        euse = pkg.get_actual_use_flags()
        instuse = pkg.get_installed_use_flags()

        for use in pkg_flags:
            exp = pkg.use_expanded(use, suggest = actual_exp)
            if exp is not None:
                if exp != actual_exp:
                    actual_exp_it = store.append(None, [None, None, exp, "<i>%s</i>" % _("This is an expanded use flag and cannot be selected"), False])
                    actual_exp = exp
            else:
                actual_exp_it = None
                actual_exp = None

            enabled = use in euse
            installed = use in instuse
            store.append(actual_exp_it, [enabled, installed, use, system.get_use_desc(use, pkg.get_cp()), True])

        return store

    def refresh_stores (self):
        """
        Refreshes the category and package stores.
        """
        self.fill_cat_store()

        if self.selCatName:
            self.fill_pkg_store(name = self.selCatName)
        else: # no selCatName -> so no category selected --> ignore
            debug("No category selected --> should be no harm.")

    def build_type_combo (self):
        model = gtk.ListStore(int, str)
        for k,v in self.db.TYPES.iteritems():
            model.append((k,v))

        self.typeCombo.set_model(model)
        cell = gtk.CellRendererText()
        self.typeCombo.pack_start(cell)
        self.typeCombo.set_attributes(cell, text = 1)


        for i, (k, v) in enumerate(model):
            if k == self.db.type: break

        self.typeCombo.set_active(i)

        types = self.db.search_types()
        if types == 1 or types % 2 == 0:
            self.typeCombo.set_sensitive(False)

    def load_session(self, sessionEx = None, defaults_only = False):
        """
        Loads the session data.
        """
        try:
            self.session = Session("gui.cfg", name="GUI", oldfiles=["gtk_session.cfg"])
        except (OSError, IOError), e:
            dialogs.io_ex_dialog(e)
            return

        oldVersion = SESSION_VERSION
        allowedVersions = (1,3,4)

        if not defaults_only and sessionEx and isinstance(sessionEx, SessionException):
            if sessionEx.got in allowedVersions:
                info(_("Translating session from version %d to %d.") % (sessionEx.got, sessionEx.expected))
                oldVersion = sessionEx.got
            else:
                warning(_("Cannot translate session from version %d to %d.") % (sessionEx.got, sessionEx.expected))
                raise sessionEx

        #
        # the callbacks for the different session variables
        #

        # QUEUE
        def load_queue (merge, unmerge, oneshot):
            def _load(q, **kwargs):
                if q:
                    for i in q.split(","):
                        self.queue.append(i, **kwargs)

            _load(merge)
            _load(unmerge, unmerge = True)
            _load(oneshot, oneshot = True)
            
        def save_queue ():
            if self.__save_queue:
                return (",".join(self.queue.mergequeue), ",".join(self.queue.unmergequeue), ",".join(self.queue.oneshotmerge))
            else:
                return ("", "", "")

        # PANED
        def load_paned (*pos):
            pos = map(int, pos)
            [x.set_position(p) for x,p in zip((self.vpaned, self.hpaned), pos)]

        def save_paned ():
            return [x.get_position() for x in (self.vpaned, self.hpaned)]

        # SELECTION
        def load_pkg_selection (name):
            pos = "0"

            if name and oldVersion > 1: # newer one
                name, pos = name.split("@")

            self.jump_to_pkg(name, pos)

        def load_cat_selection (name):
            pos = "0"

            if name and oldVersion > 1: # newer one
                name, pos = name.split("@")

            self.jump_to_cat(name, pos)

        def save_pkg_selection ():
            store, iter = self.pkgList.get_selection().get_selected()
            if iter:
                return "%s@%s" % (store.get_value(iter, 1), store.get_string_from_iter(iter))
            else:
                return ""

        def save_cat_selection ():
            # try to find the correct category using the pkgList selection
            # so we do not select ALL =)
            # if no package has been selected - return selCatName

            catStore, catIter = self.catList.get_selection().get_selected()
            pkgStore, pkgIter = self.pkgList.get_selection().get_selected()
            if pkgIter:
                pkgVal = pkgStore.get_value(pkgIter, 2)
                pos = "0"

                if catIter: # check for the more exact category position if possible
                    catVal = catStore.get_value(catIter, 0)
                    catParent = self.catList.get_model().iter_parent(catIter)

                    if catParent:
                        catVal = "%s-%s" % (catStore.get_value(catParent, 0), catVal)
                    
                    if catVal == pkgVal: # the info in the pkgList has higher precedence
                        pos = catStore.get_string_from_iter(catIter)

                return "%s@%s" % (pkgVal, pos)
            else:
                return "%s@0" % self.selCatName

        # PLUGIN
        def load_plugin (p):
            def _load(val):
                if val:
                    p.status = int(val)*2

            return _load
        
        def save_plugin (p):
            def _save ():
                if p.status == p.STAT_HARD_DISABLED:
                    return ""

                return int(p.status >= p.STAT_ENABLED)
            
            return _save

        # SEARCH TYPE
        def load_search_type (t):
            t = int(t)
            try:
                self.db.type = t
            except UnsupportedSearchTypeError:
                info("Cannot set search type. '%s' not supported by database '%s'.", t, self.db.__class__.__name__)

        # SESSION VERSION
        def load_session_version (version):

            if oldVersion < 4:
                self.session.rename_section("window", "GUI")

            if oldVersion != SESSION_VERSION: # we are trying to convert
                return
            
            version = int(version)

            if version < SESSION_VERSION:
                raise OldSessionException(version, SESSION_VERSION)
            elif version > SESSION_VERSION:
                raise NewSessionException(version, SESSION_VERSION)

        def _add (value):
            if len(value) == 4:
                self.session.add_handler(value[:3], default = value[3])
            else:
                self.session.add_handler(value)

        # set the simple ones :)
        map(_add,[
            ([("gtksessionversion", "session")], load_session_version, lambda: SESSION_VERSION),
            (["width", "height"], lambda w,h: self.window.resize(int(w), int(h)), self.window.get_size),
            (["vpanedpos", "hpanedpos"], load_paned, save_paned),
            (["catsel"], load_cat_selection, save_cat_selection, ["app-portage@0"]),
            (["pkgsel"], load_pkg_selection, save_pkg_selection, ["portato@0"]),
            (["searchtype"], load_search_type, lambda: self.db.type)
            #([("merge", "queue"), ("unmerge", "queue"), ("oneshot", "queue")], load_queue, save_queue),
            ])

        # set the plugins
        queue = plugin.get_plugin_queue()
        if queue:
            for p in queue.get_plugins():
                self.session.add_handler(([(p.name.replace(" ","_").replace(":","_"), "plugins")], load_plugin(p), save_plugin(p)))

        # the other things
        def load_cfg ((name, cat)):
            def load (v):
                self.cfg.set_session(name, cat, v)

            def save ():
                v = self.cfg.get_session(name, cat)
                if v is None:
                    return ""
                else:
                    return v

            self.session.add_handler(([(name, cat)], load, save))

        map(load_cfg, [("prefheight", "GUI"), ("prefwidth", "GUI")])

        # now we have the handlers -> load
        self.session.load(defaults_only)
    
    def jump_to (self, cp, version = None):
        """
        Is called when we want to jump to a specific package.

        @param cp: the CP to jump to
        @type cp: string
        @param version: if not None jump to a specific version
        @type version: string
        """

        cat, pkg = cp.split("/")

        self.jump_to_cat(cat)
        self.jump_to_pkg(pkg)
        
        self.show_package(cp = cp, version = version, queue = self.queue)

    def _jump_check_search (self, model, pos, elsef):
        try:
            row = model[pos]
        except IndexError: # position not in model
            debug("Position is too large for model")
            return True
        else:
            return elsef(row)

    def jump_to_pkg (self, name = None, pos = "0"):
        if isinstance(pos, int):
            pos = str(pos)
        
        col = 1
        model = self.pkgList.get_model()

        if not len(model): # model is no real list, so "not model" won't work
            return

        if name:
            if self._jump_check_search(model, pos, lambda r: r[col] != name):
                debug("Pkg path does not match. Searching...")
                for cname, path in ((x[col], x.path) for x in model):
                    if cname == name:
                        pos = path
                        break

        debug("Selecting pkg path '%s'. Value: '%s'", pos, model[pos][col])
        self.pkgList.get_selection().select_path(pos)
        self.pkgList.scroll_to_cell(pos)

    def jump_to_cat (self, name = None, pos = "0"):
        if isinstance(pos, int):
            pos = str(pos)
        
        col = 0
        model = self.catList.get_model()

        if not len(model): # model is no real list, so "not model" won't work
            return

        if name:
            if self.cfg.get_boolean("collapseCats", "GUI"):
                sname = name.split("-", 1)

                if len(sname) < 2:
                    sname = None
            else:
                sname = None

            if sname is None and self._jump_check_search(model, pos, lambda r: r[col] != name): # need to search in normal list
                debug("Cat path does not match. Searching...")
                for cname, path in ((x[col], x.path) for x in model):
                    if cname == name:
                        pos = path
                        break
            
            elif sname: # the collapse case
                p = pos.split(":")[0]
                no_match = False
                
                if self._jump_check_search(model, p, lambda r: r[col] != sname[0]):
                    debug("First part of cat path does not match. Searching...")
                    no_match = True
                    for r in model:
                        if r[col] == sname[0]:
                            row = r
                            break
                    else:
                        row = model[0]
                else:
                    row = model[p]

                if no_match or self._jump_check_search(model, pos, lambda r: r[col] != sname[1]):
                    debug("Second part of cat path does not match. Searching...")
                    for cname, path in ((x[col], x.path) for x in row.iterchildren()):
                        if cname == sname[1]: # found second
                            pos = ":".join(map(str,path))
                            break
                
                if ":" in pos:
                    self.catList.expand_to_path(pos)

        debug("Selecting cat path '%s'. Value: '%s'", pos, model[pos][col])
        self.catList.get_selection().select_path(pos)
        self.catList.scroll_to_cell(pos)

    def set_color (self, color):
        """
        Sets the color of the general VB (i.e. the thing that displays the package details)

        @param color: color to set it to
        @type color: gtk.gdk.Color
        """

        generalVB = self.tree.get_widget("generalVB")
        generalVB.modify_bg(gtk.STATE_NORMAL, color)

    def set_uri_hook (self, browser):
        """
        Sets the browser command which is called when a URL is going to be opened.

        @param browser: the browser command
        @type browser: string
        """

        browser = browser.split()
        gtk.link_button_set_uri_hook(lambda btn, x: get_listener().send_cmd(browser+[btn.get_uri()]))

    def set_notebook_tabpos (self, tabposlist):
        """
        Sets the positions of the tabs of the notebooks.

        @param tabposlist: the list of positions: first comes the one for package tabs; sndly for sys tabs
        @type tabposlist: int[]
        """
        self.pkgNotebook.set_tab_pos(tabposlist[0])
        self.sysNotebook.set_tab_pos(tabposlist[1])

    def title_update (self, title):
        """
        Updates the titles of the window and the systray.
        Mainly used with emerge term titles.

        @param title: the title
        @type title: string
        """
        
        def window_title_update (title):
            """
            Updates the title of the main window.
            """
            if title is None or not self.cfg.get_boolean("updateTitle", "GUI"):
                self.window.set_title(self.main_title)
            else:
                title = title.strip()
                if title[0] == '*':
                    self.window.set_title(self.main_title)
                else:
                    space_idx = title.rfind(" ")
                    if space_idx != -1:
                        title = title[:space_idx]

                    self.window.set_title(("Portato >>> %s" % title))

        def __update(title):
            if self.tray:
                self.tray.set_tooltip(title)
            
            window_title_update(title)
            if title is None or not self.cfg.get_boolean("updateConsole", "GUI"):
                title = _("Console")
            else:
                title = ("%s (%s)") % (_("Console"), title)
            
            tlength = int(self.cfg.get("titlelength", "GUI"))
            if (len(title) > tlength): title = "%s..." % title[:tlength-3]
            self.sysNotebook.set_tab_label_text(self.termHB, title)

            return False

        # as this might get called from other threads use gobject.idle_add
        gobject.idle_add(__update, title)

    def cb_cat_list_selection (self, selection):
        """
        Callback for a category-list selection. 
        Updates the package list with the packages in the category.
        """
        # get the selected category
        store, it = selection.get_selected()
        if it:
            if not self.cfg.get_boolean("collapseCats", "GUI"):
                self.selCatName = store.get_value(it, 0)
            else:
                parent = store.iter_parent(it)
                if parent is None:
                    if store.iter_has_child(it): # this is a split up selector -> do nothing
                        return True
                    else:
                        self.selCatName = store.get_value(it, 0) # this is a non-split up top
                else:
                    self.selCatName = ("%s-%s" % (store.get_value(parent, 0), store.get_value(it, 0)))

            self.fill_pkg_store(name = self.selCatName)
        return True

    def cb_pkg_list_selection (self, selection):
        """
        Callback for a package-list selection.
        Updates the version list.
        """
        store, it = selection.get_selected()
        if it:
            oldcp = self.selCP

            self.selCP = "%s/%s" % (store.get_value(it, 2), store.get_value(it, 1))
            try:
                self.fill_version_list(self.selCP)
            except VersionsNotFoundException, e:
                warning(_("No versions of package '%s' found!") % self.selCP)
                dialogs.no_versions_dialog(self.selCP)
                self.db.disable(self.selCP)
                self.selCP = oldcp

        return True

    def cb_pkg_list_header_clicked(self, col):
        self.sortPkgListByName = not self.sortPkgListByName
        self.fill_pkg_store(name = self.selCatName)
        return True

    def cb_vers_list_selection (self, selection):
        """
        Callback for a package-list selection.
        Updates the version list.
        """
        store, it = selection.get_selected()
        if it:
            self.selCPV = "%s-%s" % (self.selCP, store.get_value(it, 1))
            self.show_package(cpv = self.selCPV, queue = self.queue)
        
        return True

    def cb_queue_list_selection (self, selection):

        def set_val (val):
            self.queueOneshot.handler_block(self.queueOneshotHandler)
            self.queueOneshot.set_active(val)
            self.queueOneshot.handler_unblock(self.queueOneshotHandler)

        store, it = selection.get_selected()
        if it:
            parent = self.queueTree.parent_iter(it)
            if self.queueTree.is_in_emerge(it) and parent and not self.queueTree.iter_has_parent(parent):
                package = store.get_value(it, 0)
                self.queueOneshot.set_sensitive(True)
                set_val(package in self.queue.oneshotmerge)
                return True

        self.queueOneshot.set_sensitive(False)
        set_val(False)
        return True

    def cb_queue_row_activated (self, view, path, *args):
        """Callback for an activated row in the emergeQueue. Opens a package window."""
        store = self.queueTree
        if len(path) > 1:
            iterator = store.get_original().get_iter(path)
            if store.iter_has_parent(iterator):
                package = store.get_value(iterator, store.get_cpv_column())

                if store.is_in_emerge(iterator):
                    type = "install"
                elif store.is_in_unmerge(iterator):
                    type = "uninstall"
                elif store.is_in_update(iterator):
                    type = "update"

                self.show_package(cpv = package, queue = self.queue, instantChange = True, doEmerge = False, type = type)
        return True
    
    def cb_queue_tooltip_queried (self, view, x, y, is_keyboard, tooltip):
        store = self.queueList.get_model()
        path = self.queueList.get_path_at_pos(x,y)

        if path is None:
            return False

        it = store.get_iter(path[0])

        if store.iter_parent(it) is None:
            return False # do not show tooltips for the root entries

        pkg = system.new_package(store.get_value(it, 0))
        
        enabled = []
        disabled = []
        expanded = set()

        pkg_flags = pkg.get_iuse_flags()
        pkg_flags.sort()
        if not pkg_flags: # no flags - stop here
            return None
        
        actual = set(pkg.get_actual_use_flags())
        
        if pkg.is_installed():
            installed = set(pkg.get_iuse_flags()).intersection(pkg.get_installed_use_flags())
        else:
            inst = system.find_packages(pkg.get_slot_cp(), system.SET_INSTALLED)
            if inst:
                installed = set(inst[0].get_iuse_flags()).intersection(inst[0].get_installed_use_flags())
            else:
                installed = set()

        diff = actual.symmetric_difference(installed)

        for use in pkg_flags:
            exp = pkg.use_expanded(use)
            if exp:
                expanded.add(exp)
            
            else:
                useStr = use
                if installed and use in diff:
                    useStr += " %"
                if use in actual:
                    enabled.append(useStr)
                else:
                    disabled.append(useStr)
        
        string = ""
        
        if enabled:
            string = "<b>+%s</b>" % ("\n+".join(enabled),)
            if len(disabled) > 0:
                string = string + "\n"
        
        if disabled:
            string = string+"<i>- %s</i>" % ("\n- ".join(disabled),)

        if expanded:
            if string:
                string += "\n\n"

            string += "\n".join(expanded)
        
        tooltip.set_markup(string)
        return string != ""

    def cb_execute_clicked (self, action):
        """Execute the current queue."""
        
        if len(flags.newUseFlags) > 0:
            if not self.session.get_bool("useflags", "dialogs"):
                self.session.set("useflags", str(dialogs.changed_flags_dialog(_("use flags"))[1]), "dialogs")
            try:
                flags.write_use_flags()
            except IOError, e:
                dialogs.io_ex_dialog(e)
                return True
        
        if len(flags.new_masked)>0 or len(flags.new_unmasked)>0 or len(flags.newTesting)>0:
            debug("new masked: %s",flags.new_masked)
            debug("new unmasked: %s", flags.new_unmasked)
            debug("new testing: %s", flags.newTesting)
            if not self.session.get_bool("keywords", "dialogs"):
                self.session.set("keywords", str(dialogs.changed_flags_dialog(_("masking keywords"))[1]), "dialogs")
            try:
                flags.write_masked()
                flags.write_testing()
            except IOError, e:
                dialogs.io_ex_dialog(e)
                return True
            else:
                system.reload_settings()

        model, iter = self.queueList.get_selection().get_selected()

        if iter is None:
            if model.iter_n_children(None) == 1: # only one queue there - take this as being selected
                iter = model.get_iter_root()
            else:
                return False

        self.sysNotebook.set_current_page(self.CONSOLE_PAGE)
        
        # test which type of queue we have here
        if self.queueTree.is_in_emerge(iter):
            self.queue.emerge(force = True)
        elif self.queueTree.is_in_unmerge(iter):
            self.queue.unmerge(force = True)
        else:
            self.queue.update_world(sets = self.updateSets, force=True, newuse = self.cfg.get_boolean("newuse"), deep = self.cfg.get_boolean("deep"))

        return True
        
    def cb_update_clicked (self, action):
        def __update():
            
            def cb_idle_append (updating):
                try:
                    try:
                        for pkg, old_pkg in updating:
                            self.queue.append(pkg.get_cpv(), type = "update", unmask = False)
                    except PackageNotFoundException, e:
                        if dialogs.unmask_dialog(e[0]) == gtk.RESPONSE_YES:
                            for pkg, old_pkg in updating:
                                self.queue.append(pkg.get_cpv(), type = "update", unmask = True)

                except BlockedException, e:
                    dialogs.blocked_dialog(e[0], e[1])
                    self.queue.remove_children(self.queueTree.get_update_it())
                
                return False

            watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
            self.window.window.set_cursor(watch)
            try:
                if system.has_set_support():
                    confsets = [x.strip() for x in self.cfg.get("updatesets").split(",")]
                    self.updateSets = [s for s in confsets if s in system.get_sets()]
                    updating = system.update_world(sets = self.updateSets, newuse = self.cfg.get_boolean("newuse"), deep = self.cfg.get_boolean("deep"))
                else:
                    updating = system.update_world(newuse = self.cfg.get_boolean("newuse"), deep = self.cfg.get_boolean("deep"))
                    self.updateSets = ("world",)
                
                debug("updating list: %s --> length: %s", [(x.get_cpv(), y.get_cpv()) for x,y in updating], len(updating))
                gobject.idle_add(cb_idle_append, updating)
            finally:
                self.window.window.set_cursor(None)
        
        # for some reason, I have to create the thread before displaying the dialog
        # else the GUI hangs
        t = GtkThread(name="Update-Thread", target=__update)

        if not self.session.get_bool("update_world_warning", "dialogs"):
            self.session.set("update_world_warning", str(dialogs.update_world_warning_dialog()[1]), "dialogs")

        t.start()
        
        return True

    def cb_remove_clicked (self, button):
        """Removes a selected item in the (un)emerge-queue if possible."""
        model, iter = self.queueList.get_selection().get_selected()

        if iter:
            parent = model.iter_parent(iter)
            
            if self.queueTree.is_in_update(iter) and parent:
                if dialogs.remove_updates_dialog() == gtk.RESPONSE_YES:
                    self.queue.remove_with_children(self.queueTree.get_update_it())
            
            elif not parent: # top-level
                if model.iter_n_children(iter) > 0: # and has children which can be removed :)
                    if dialogs.remove_queue_dialog() == gtk.RESPONSE_YES :
                        self.queue.remove_with_children(iter)
                else:
                    self.queue.remove(iter)
            
            elif model.iter_parent(parent): # this is in the 3rd level => dependency
                dialogs.remove_deps_dialog()
            else:
                self.queue.remove_with_children(iter)

                if model.iter_n_children(parent) == 0: # no more children left - remove queue too
                    self.queue.remove(parent)
        
            return True
        return False

    def cb_sync_clicked (self, action):
        self.sysNotebook.set_current_page(self.CONSOLE_PAGE)
        cmd = self.cfg.get("syncCommand")

        if cmd != "emerge --sync":
            cmd = cmd.split()
            self.queue.sync(cmd)
        else:
            self.queue.sync()

    def cb_save_flags_clicked (self, action):
        try:
            flags.write_use_flags()
            flags.write_testing()
            flags.write_masked()
        except IOError, e:
            dialogs.io_ex_dialog(e)

    @Window.watch_cursor
    def cb_reload_clicked (self, action):
        """Reloads the portage settings and the database."""
        system.reload_settings()
        self.db.reload()

    @Window.watch_cursor
    def cb_search_clicked (self, entry):
        """Do a search."""
        text = entry.get_text()
        if text:
            oldr = self.db.restrict
            self.db.restrict = text
            packages = list("/".join((p.cat,p.pkg)) for p in self.db.get_cat())
            self.db._restrict = oldr # don't do the rewriting again

            if packages == []:
                dialogs.nothing_found_dialog()
            else:
                if len(packages) == 1:
                    self.jump_to(packages[0])
                else:
                    SearchWindow(self.window, packages, self.jump_to)

        return True

    def cb_search_changed (self, *args):
        """
        Called when the user enters something in the search field.
        Updates the packages according to the search expression.
        """
        if not self.__searchChanged and self.cfg.get_boolean("searchOnType", section="GUI"):
            self.__searchChanged = True
            
            def __update():
                self.__searchChanged = False
                txt = self.searchEntry.get_text()

                if txt or self.db.restrict:
                    self.db.restrict = txt

                    self.refresh_stores()
                    self.catList.get_selection().select_path("0") # XXX make this smarter

                return False # not again ;)

            gobject.timeout_add(200, __update)

    def cb_type_combo_changed (self, *args):
        model = self.typeCombo.get_model()
        active = self.typeCombo.get_active()

        self.db.type = model[active][0]
        self.cb_search_changed()

    def cb_delete_search_clicked (self, *args):
        self.searchEntry.set_text("")
        return True

    def cb_preferences_clicked (self, *args):
        """
        User wants to open preferences.
        """
        PreferenceWindow(self.window, self.cfg, self.console.set_font_from_string, self.set_uri_hook, self.set_notebook_tabpos, self.fill_cat_store, self.set_color)
        return True

    def cb_about_clicked (self, *args):
        """
        User wants to open about dialog.
        """
        AboutWindow(self.window)
        return True

    def cb_plugins_clicked (self, *args):
        """
        User wants to open plugin dialog.
        """
        queue = plugin.get_plugin_queue()
        if queue is None:
            plugins = []
        else:
            plugins = list(sorted(queue.get_plugins(), key = op.attrgetter("name")))

        PluginWindow(self.window, plugins, self.queue)
        return True

    def show_package_list (self, pkg_generator, klass, thread_name = "PkgList Update Thread"):
        
        def cb_idle_show(packages):
            """
            Callback opening the menu when the calculation is finished.

            @returns: False to signal that it is finished
            """
            klass(self.window, packages, self.queue, self.jump_to)
            return False
        
        def __update():
            watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
            self.window.window.set_cursor(watch)
            
            packages = []
            try:
                packages.extend(pkg_generator())
            finally:
                self.window.window.set_cursor(None)

            gobject.idle_add(cb_idle_show, packages)
        
        GtkThread(name = thread_name, target = __update).start()
        return True
    
    def cb_show_updates_clicked (self, *args):
        """
        Show the list of updateble packages.
        """

        self.show_package_list(
                lambda: (x.get_cpv() for x in system.get_updated_packages()),
                UpdateWindow, "Show Updates Thread")

        return True

    def cb_show_world_clicked (self, *args):
        """
        Show the list of world packages.
        """
        self.show_package_list(
                lambda: system.find_packages(pkgSet = "world", only_cpv = True),
                WorldListWindow)

        return True

    def cb_show_installed_toggled (self, *args):
        """
        Toggle the "show only installed" option.
        """
        self.showAll = not self.showAll
        self.refresh_stores()

    def cb_right_click (self, object, event):
        """
        Called when the user right clicks somewhere.
        Used to display a menu.
        
        This method should handle ALL such menus.

        @param object: the object/widget where the click is done
        @type object: gtk.Widget
        @param event: the event triggered
        @type event: gtk.gdk.Event
        """

        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3: # 3 == right click
            x = int(event.x)
            y = int(event.y)
            time = event.time
            
            if object == self.console:
                self.consolePopup.popup(None, None, None, event.button, time)
            else:
                return False
        else:
            return False

    def cb_oneshot_clicked (self, *args):
        """
        Mark a package as oneshot.
        """
        sel = self.queueList.get_selection()
        store, it = sel.get_selected()
        if it:
            if self.queueTree.is_in_emerge(it) and self.queueTree.iter_has_parent(it):
                package = store.get_value(it, 0)
                set = (package not in self.queue.oneshotmerge)
                
                self.queue.append(package, update = True, oneshot = set, forceUpdate = True)

    def cb_pause_emerge (self, action):
        # pause or continue
        self.emergePaused = action.get_active()
        if not self.emergePaused:
            self.queue.continue_emerge()
        else:
            self.queue.stop_emerge()

    def cb_kill_clicked (self, *args):
        """
        Kill emerge.
        """
        self.queue.kill_emerge()
        if self.emergePaused: # unmark the "pause emerge" buttons
            self.tree.get_widget("generalActionGroup").get_action("pauseAction").set_active(False)

    def cb_copy_clicked (self, *args):
        """
        Copy marked text in the terminal to clipboard.
        """
        self.console.copy_clipboard()

    def cb_delete (self, *args):
        """
        Called when the user wants to quit the application.

        Asks the user for confirmation if there is something in the queue.
        Also saves session data.
        """

        self.__save_queue = False

        if not self.queue.is_empty():
            ret = dialogs.queue_not_empty_dialog()
            if ret == gtk.RESPONSE_CANCEL:
                return True
            else: # there is sth in queue AND the user still wants to close -> kill emerge
                self.__save_queue = (ret == gtk.RESPONSE_YES)
                self.queue.kill_emerge()

        # write sessions
        Session.close()
        
        return False

    def cb_minimized (self, window, event):
        """
        User wants to minimize the window. 
        If it is possible to minimize to tray, it is done.
        """

        if self.tray and self.cfg.get_boolean("hideOnMinimize", "GUI"):
            if event.changed_mask & gtk.gdk.WINDOW_STATE_ICONIFIED:
                if event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED:
                    self.window.hide()
                    return True
        
        return False

    def cb_systray_activated (self, *args):
        """
        Systray was activated. Show or hide the window.
        """
        if self.window.iconify_initially:
            self.window.deiconify()
            self.window.show()
            self.window.window.show()
        else:
            self.window.iconify()
    
    def cb_testing_toggled (self, *args):
        return self.packageTable.cb_testing_toggled(*args)
    def cb_masked_toggled (self, *args):
        return self.packageTable.cb_masked_toggled(*args)
    def cb_button_pressed (self, *args):
        return self.packageTable.cb_button_pressed(*args)
    def cb_package_revert_clicked (self, *args):
        return self.packageTable.cb_package_revert_clicked(*args)
    def cb_package_unmerge_clicked (self, *args):
        return self.packageTable.cb_package_unmerge_clicked(*args)
    def cb_package_emerge_clicked (self, *args):
        return self.packageTable.cb_package_emerge_clicked(*args)
    def cb_use_flag_toggled (self, *args):
        return self.packageTable.cb_use_flag_toggled(*args)

    def cb_close (self, *args):
        """
        "Close" menu entry called.
        Emulate normal quitting.
        """
        if not self.cb_delete(): # do the checks
            self.window.destroy()

    def cb_destroy (self, *args):
        """
        Calls main_quit().
        """
        gtk.main_quit()

    def check_prereqs (self):

        def fail (m):
            error("PreReqError: %s", m)
            raise PreReqError(m)

        pdir = system.get_global_settings("PORTDIR")

        if not os.path.exists(pdir):
            fail(_("The portage tree is not existing."))

        ls = os.listdir(system.get_global_settings("PORTDIR"))
        if not "eclass" in ls:
            fail(_("The portage tree seems to be empty."))

        if 'sqlite' in system.settings.settings.modules['user'].get('portdbapi.auxdbmodule', ''):
            fail(_("The sqlite cache backend of portage is not supported at the moment. See https://bugs.launchpad.net/portato/+bug/564292."))

        debug("All prereqs matched. Fine :)")

    def main (self):
        """
        Main.
        """
        gobject.threads_init()
        # now subthreads can run normally, but are not allowed to touch the GUI. If threads should change sth there - use gobject.idle_add().
        # for more informations on threading and gtk: http://www.async.com.br/faq/pygtk/index.py?req=show&file=faq20.006.htp
        plugin.hook("main")(gtk.main)()
