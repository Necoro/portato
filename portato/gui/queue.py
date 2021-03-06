# -*- coding: utf-8 -*-
#
# File: portato/gui/queue.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from future_builtins import map, filter, zip

# some stuff needed
import os, pty
import signal, threading, time
from subprocess import Popen

# some backend things
from .. import backend, plugin
from ..backend import flags, system
from ..backend.exceptions import BlockedException
from ..helper import debug, info, warning, error
from ..waiting_queue import WaitingQueue
from ..odict import OrderedDict
from .updater import Updater

# the wrapper
from .utils import GtkTree

class EmergeQueue:
    """This class manages the emerge queue."""
    
    def __init__ (self, tree = None, console = None, db = None, title_update = None, threadClass = threading.Thread):
        """Constructor.
        
        @param tree: Tree to append all the items to.
        @type tree: GtkTree
        @param console: Output is shown here.
        @type console: vte.Terminal
        @param db: A database instance.
        @type db: Database
        @param title_update: A function, which will be called whenever there is a title update.
        @type title_update: function(string)"""
        
        # the different queues
        self.mergequeue = [] # for emerge
        self.unmergequeue = [] # for emerge -C
        self.oneshotmerge = [] # for emerge --oneshot
        
        # the emerge process
        self.process = None
        self.threadQueue = WaitingQueue(threadClass = threadClass)
        self.pty = None

        # dictionaries with data about the packages in the queue
        self.iters = {"install" : {}, "uninstall" : {}, "update" : {}} # iterator in the tree
        self.deps = {"install" : {}, "update" : {}} # all the deps of the package
        self.blocks = {"install" : OrderedDict(), "update" : OrderedDict()}
        
        # member vars
        self.tree = tree
        if self.tree and not isinstance(self.tree, GtkTree): raise TypeError("tree passed is not a GtkTree-object")
        
        self.console = console
        
        self.db = db
        self.title_update = title_update
        self.threadClass = threadClass
        
        if self.console:
            self.pty = pty.openpty()
            self.console.set_pty(self.pty[0])

    def _get_pkg_from_cpv (self, cpv, unmask = False):
        """Gets a L{backend.Package}-object from a cpv.

        @param cpv: the cpv to get the package for
        @type cpv: string (cpv)
        @param unmask: if True we will look for masked packages if we cannot find unmasked ones
        @type unmask: boolean
        @return: created package
        @rtype: backend.Package
        
        @raises backend.PackageNotFoundException: If no package could be found - normally it is existing but masked."""

        # for the beginning: let us create a package object - but it is not guaranteed, that it actually exists in portage
        pkg = system.new_package(cpv)
        masked = not (pkg.is_masked() or pkg.is_testing(use_keywords=True)) # we are setting this to True in case we have unmasked it already, but portage does not know this
        
        # and now try to find it in portage
        pkg = system.find_packages("="+cpv, masked = masked)
        
        if pkg: # gotcha
            pkg = pkg[0]

        elif unmask: # no pkg returned, but we are allowed to unmask it
            pkg = system.find_packages("="+cpv, masked = True)

            if not pkg:
                raise backend.PackageNotFoundException(cpv) # also not found
            else:
                pkg = pkg[0]

            if pkg.is_testing(use_keywords = True):
                pkg.set_testing(True)
            if pkg.is_masked():
                pkg.set_masked()
        
        else: # no pkg returned - and we are not allowed to unmask
            raise backend.PackageNotFoundException(cpv)
        
        return pkg
    
    def update_tree (self, it, cpv, unmask = False, oneshot = False, type = "install"):
        """This updates the tree recursivly, or? Isn't it? Bjorn!

        @param it: iterator where to append
        @type it: Iterator
        @param cpv: The package to append.
        @type cpv: string (cat/pkg-ver)
        @param unmask: True if we are allowed to look for masked packages
        @type unmask: boolean
        @param oneshot: True if we want to emerge is oneshot
        @type oneshot: boolean
        @param type: the type of the updating
        @type type: string
        
        @raises backend.BlockedException: When occured during dependency-calculation.
        @raises backend.PackageNotFoundException: If no package could be found - normally it is existing but masked."""
        
        if cpv in self.deps[type]:
            return # in list already and therefore it's already in the tree too    
        
        # try to find an already installed instance
        update = False
        downgrade = False
        uVersion = None
        changedUse = []
        try:
            pkg = self._get_pkg_from_cpv(cpv, unmask)
            if not pkg.is_installed():
                old = system.find_packages(pkg.get_slot_cp(), system.SET_INSTALLED)
                if old:
                    old = old[0] # assume we have only one there
                    cmp = pkg.__cmp__(old)
                    if cmp > 0:
                        update = True
                    elif cmp < 0:
                        downgrade = True

                    uVersion = old.get_version()

                    old_iuse = set(old.get_iuse_flags())
                    new_iuse = set(pkg.get_iuse_flags())

                    for i in old_iuse.difference(new_iuse):
                        changedUse.append("-"+i)

                    for i in new_iuse.difference(old_iuse):
                        changedUse.append("+"+i)
            else:
                old_iuse = set(pkg.get_iuse_flags(installed = True))
                new_iuse = set(pkg.get_iuse_flags(installed = False))

                for i in old_iuse.difference(new_iuse):
                    changedUse.append("-"+i)

                for i in new_iuse.difference(old_iuse):
                    changedUse.append("+"+i)

        except backend.PackageNotFoundException as e: # package not found / package is masked -> delete current tree and re-raise the exception
            if type == "update": # remove complete tree
                self.remove_with_children(self.tree.first_iter(it), removeNewFlags = False)
            
            elif type == "install": # remove only the intentionally added package
                top = self.tree.first_iter(it)
                parent = self.tree.parent_iter(it)
                
                if parent:
                    while not self.tree.iter_equal(top, parent):
                        parent = self.tree.parent_iter(parent)
                        it = self.tree.parent_iter(it)

                    self.remove_with_children(it, removeNewFlags = False)

                if not self.tree.iter_has_children(top): # remove completely if nothing left
                    self.remove(top)
            raise

        # get dependencies
        deps = pkg.get_dep_packages(return_blocks = True)
        self.deps[type][cpv] = deps
        
        # add iter
        subIt = self.tree.append(it, self.tree.build_append_value(cpv, oneshot = oneshot, update = update, downgrade = downgrade, version = uVersion, useChange = changedUse))
        self.iters[type][cpv] = subIt
        
        for d in deps:
            if d[0] == "!": # block
                dep = d[1:]
                if not dep in self.blocks[type]:
                    self.blocks[type][dep] = set()

                self.blocks[type][dep].add(cpv)
            else: # recursive call
                self.update_tree(subIt, d, unmask, type = type)
        
    def append (self, cpv, type = "install", update = False, forceUpdate = False, unmask = False, oneshot = False):
        """Appends a cpv either to the merge queue or to the unmerge-queue.
        Also updates the tree-view.
        
        @param cpv: Package to add
        @type cpv: string (cat/pkg-ver)
        @param type: The type of this append process. Possible values are "install", "uninstall", "update".
        @type type: string        
        @param update: Set to True if a package is going to be updated (e.g. if the use-flags changed).
        @type update: boolean
        @param forceUpdate: Set to True if the update should be forced.
        @type forceUpdate: boolean
        @param unmask: True if we are allowed to look for masked packages
        @type unmask: boolean
        @param oneshot: True if this package should not be added to the world-file.
        @type oneshot: boolean
        
        @raises portato.backend.PackageNotFoundException: if trying to add a package which does not exist"""
        
        if type in ("install", "update"): # emerge
            if update:
                pkg = self._get_pkg_from_cpv(cpv, unmask)
                deps = pkg.get_dep_packages(return_blocks = True)
                
                if not forceUpdate and cpv in self.deps[type] and deps == self.deps[type][cpv]:
                    return # nothing changed - return
                else:
                    hasBeenInQueue = (cpv in self.mergequeue or cpv in self.oneshotmerge)
                    parentIt = self.tree.parent_iter(self.iters[type][cpv])

                    # delete it out of the tree - but NOT the changed flags
                    self.remove_with_children(self.iters[type][cpv], removeNewFlags = False)
                    
                    if hasBeenInQueue: # package has been in queue before
                        self._queue_append(cpv, oneshot)
                    
                    self.update_tree(parentIt, cpv, unmask, oneshot = oneshot, type = type)
            else: # not update
                if type == "install":
                    if self.tree:
                        self.update_tree(self.tree.get_emerge_it(), cpv, unmask, type = type, oneshot = oneshot)
                    self._queue_append(cpv, oneshot)
                elif type == "update" and self.tree:
                    self.update_tree(self.tree.get_update_it(), cpv, unmask, type = type, oneshot = oneshot)

            # handle blocks
            if self.blocks[type]:
                # check whether anything blocks something in the queue
                for block in self.blocks[type]:
                    for c in self.iters[type]:
                        if system.cpv_matches(c, block):
                            blocked = ", ".join(self.blocks[type][block])
                            warning("'%s' is blocked by: %s", c, blocked)
                            self.remove_with_children(self.iters[type][c], False)
                            raise BlockedException(c, blocked)

                #
                # check whether we block a version that we are going to replace nevertheless
                #
                
                # get the blocks that block an installed package
                inst = []
                for block in self.blocks[type]:
                    pkgs = system.find_packages(block, system.SET_INSTALLED)
                    if pkgs:
                        inst.append((pkgs, block))

                # the slot-cp's of the packages in the queue
                slots = {}
                for c in self.iters[type]:
                    slots[system.new_package(c).get_slot_cp()] = c

                # check the installed blocks against the slot-cp's
                for pkgs, block in inst[:]:
                    done = False
                    for pkg in pkgs:
                        done = False
                        if pkg.get_slot_cp() in slots:
                            debug("Block '%s' can be ignored, because the blocking package is going to be replaced with '%s'.", block, slots[pkg.get_slot_cp()])
                            done = True
                    if done:
                        inst.remove((pkgs,block))

                if inst: # there is still something left to block
                    for pkgs, block in inst:
                        blocked = ", ".join(self.blocks[type][block])
                        warning("'%s' blocks the installation of: %s", pkgs[0].get_cpv(), blocked)
                        self.remove_with_children(self.iters[type][cpv], False)
                        raise BlockedException(blocked, pkgs[0].get_cpv())
            
        else: # unmerge
            if cpv not in self.unmergequeue:
                self.unmergequeue.append(cpv)
                if self.tree: # update tree
                    self.iters["uninstall"][cpv] = self.tree.append(self.tree.get_unmerge_it(), self.tree.build_append_value(cpv))

    def _queue_append (self, cpv, oneshot = False):
        """Convenience function appending a cpv either to self.mergequeue or to self.oneshotmerge.

        @param cpv: cpv to add
        @type cpv: string (cpv)
        @param oneshot: True if this package should not be added to the world-file.
        @type oneshot: boolean"""

        if not oneshot:
            if cpv not in self.mergequeue:
                self.mergequeue.append(cpv)
        else:
            if cpv not in self.oneshotmerge:
                self.oneshotmerge.append(cpv)

    def doEmerge (self, options, packages, its, *args, **kwargs):
        top = None
        if self.tree and its:
            for v in its.values():
                self.tree.set_in_progress(v)
                top = self.tree.first_iter(v)
                break

        self.threadQueue.put(self.__emerge, options, packages, its, top, *args, **kwargs)
    
    def __emerge (self, options, packages, its, top, command = None):
        """Calls emerge and updates the terminal.
        
        @param options: options to send to emerge
        @type options: string[]
        @param packages: packages to emerge
        @type packages: string[]
        @param its: Iterators which point to these entries whose children will be removed after completion.
        @type its: dict(string -> Iterator)
        @param top: The top iterator
        @type top: Iterator
        @param command: the command to execute - default is "/usr/bin/python /usr/bin/emerge"
        @type command: string[]"""

        @plugin.hook("emerge", packages = packages, command = command, console = self.console, title_update = self.title_update)
        def sub_emerge(command):
            if command is None:
                command = system.get_merge_command()

            # open tty
            if self.console:
                self.console.reset(True, True)

            def pre ():
                os.setsid() # new session
                if self.console:
                    import fcntl, termios
                    fcntl.ioctl(self.pty[1], termios.TIOCSCTTY, 0) # set pty-slave as session tty
                    os.dup2(self.pty[1], 0)
                    os.dup2(self.pty[1], 1)
                    os.dup2(self.pty[1], 2)

            # get all categories that are being touched during the emerge process
            cats = set(x.split("/")[0] for x in its.keys())

            # start emerge
            self.process = Popen(command+options+packages, shell = False, env = system.get_environment(), preexec_fn = pre)

            # remove packages from queue
            if self.tree and its and not self.tree.is_in_unmerge(top):
                self.up = Updater(self, its, self.threadClass)
            else:
                self.up = None
            
            # update title
            if self.console:
                old_title = self.console.get_window_title()
                while self.process and self.process.poll() is None:
                    if self.title_update:
                        title = self.console.get_window_title()
                        if title != old_title:
                            self.title_update(title)
                            old_title = title
                        time.sleep(0.5)

            if self.up:
                self.up.stop()
                if its:
                    self.tree.set_in_progress(top, False)
                else:
                    self.remove(top)
            elif self.tree and its:
                self.remove_with_children(top)

            if self.title_update: self.title_update(None)

            if self.process is None: # someone resetted this
                self.threadQueue.next()
                return
            else:
                ret = self.process.returncode
                self.process = None
                self.threadQueue.next()

            @plugin.hook("after_emerge", packages = packages, retcode = ret)
            def update_packages():
                if self.db:
                    for cat in cats:
                        self.db.reload(cat)
                        debug("Category %s refreshed", cat)

            update_packages()
            
        sub_emerge(command)

    def emerge (self, force = False, options = None):
        """Emerges everything in the merge-queue.
        
        @param force: If False, '-pv' is send to emerge. Default: False.
        @type force: boolean
        @param options: Additional options to send to the emerge command
        @type options: string[]"""
        
        def prepare(queue):
            """Prepares the list of iterators and the list of packages."""
            list = []
            its = {}
            for k in queue:
                list += ["="+k]
                if self.tree:
                    its.update({k : self.iters["install"][k]})

            return list, its

        if self.tree:
            ownit = self.iters["install"]
        else:
            ownit = {}

        # oneshot-queue
        if self.oneshotmerge:
            # prepare package-list for oneshot
            list, its = prepare(self.oneshotmerge)
            if not self.mergequeue :# the other one does not exist - remove completely
                its = ownit
            
            s = system.get_oneshot_option()
            if not force: s += system.get_pretend_option()
            if options is not None: s += options
            
            self.doEmerge(s, list, its, caller = self.emerge)
        
        # normal queue
        if self.mergequeue:
            # prepare package-list
            list, its = prepare(self.mergequeue)
            if not self.oneshotmerge: # the other one does not exist - remove completely
                its = ownit

            s = []
            if not force: s = system.get_pretend_option()
            if options is not None: s += options
        
            self.doEmerge(s, list, its, caller = self.emerge)

    def unmerge (self, force = False, options = None):
        """Unmerges everything in the umerge-queue.

        @param force: If False, '-pv' is send to emerge. Default: False.
        @type force: boolean
        @param options: Additional options to send to the emerge command
        @type options: string[]"""
        
        if not self.unmergequeue: return # nothing in queue

        queue = self.unmergequeue[:] # copy the unmerge-queue
        
        # set options
        s = system.get_unmerge_option()
        if not force: s += system.get_pretend_option()
        if options is not None: s += options
        
        if self.tree:
            its = self.iters["uninstall"]
        else:
            its = {}

        self.doEmerge(s, queue, its, caller = self.unmerge)

    def update_world(self, sets = ("world",), force = False, newuse = False, deep = False, options = None):
        """Does an update world. newuse and deep are the arguments handed to emerge.

        @param sets: The sets to update.
        @type sets: string[]
        @param force: If False, '-pv' is send to emerge. Default: False.
        @type force: boolean
        @param newuse: If True, append newuse options
        @type newuse: boolean
        @param deep: If True, append deep options
        @type deep: boolean
        @param options: Additional options to send to the emerge command
        @type options: string[]"""

        opts = system.get_update_option()

        if newuse: opts += system.get_newuse_option()
        if deep: opts += system.get_deep_option()
        if not force: opts += system.get_pretend_option()
        if options is not None: opts += options

        if self.tree:
            it = self.iters["update"]
        else:
            it = {}

        self.doEmerge(opts, list(sets), it, caller = self.update_world)

    def sync (self, command = None):
        """Calls "emerge --sync".
        
        @param command: command to execute to sync. If None "emerge --sync" is taken.
        @type command: string[]"""

        if command is None:
            command = system.get_sync_command()
    
        try:
            while True:
                idx = command.index("&&")
                self.doEmerge([],[],{}, command[:idx], caller = self.sync)
                command = command[idx+1:]
        except ValueError: # no && in command
            self.doEmerge([],[],{}, command, caller = self.sync)

        # syncing portage and DB after emerge sync
        def finish ():
            debug("Finishing sync...")
            system.reload_settings()
            self.db.reload()
            debug("Sync finished")
            self.threadQueue.next()

        self.threadQueue.put(finish, caller = self.sync)

    def kill_emerge (self):
        """Kills the emerge process."""
        if self.process is not None:
            self.threadQueue.clear() # remove all pending emerge threads
            try:
                pgid = os.getpgid(self.process.pid)
                os.killpg(pgid, signal.SIGTERM)
                debug("Process should be terminated")
                if self.process.poll() is None:
                    os.killpg(pgid, signal.SIGKILL)
                    debug("Process should be killed")
            except AttributeError:
                debug("AttributeError occured ==> process not exisiting - ignore")
            except OSError:
                debug("OSError occured ==> process already stopped - ignore")

            self.process = None

    def stop_emerge (self):
        if self.process is not None:
            os.killpg(os.getpgid(self.process.pid), signal.SIGSTOP)
            debug("Process should be stopped")

    def continue_emerge (self):
        if self.process is not None:
            os.killpg(os.getpgid(self.process.pid), signal.SIGCONT)
            debug("Process should continue")

    def remove_with_children (self, it, removeNewFlags = True):
        """Convenience function which removes all children of an iterator and than the iterator itself.

        @param it: The iter which to remove.
        @type it: Iterator
        @param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
        @type removeNewFlags: boolean"""

        self.remove_children(it, removeNewFlags)
        self.remove(it, removeNewFlags)

    def remove_children (self, parentIt, removeNewFlags = True):
        """Removes all children of a given parent TreeIter recursivly.
        
        @param parentIt: The iter from which to remove all children.
        @type parentIt: Iterator
        @param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
        @type removeNewFlags: boolean"""

        childIt = self.tree.first_child_iter(parentIt)

        while childIt:
            if (self.tree.iter_has_children(childIt)): # recursive call
                self.remove_children(childIt, removeNewFlags)
            temp = childIt
            childIt = self.tree.next_iter(childIt)
            self.remove(temp, removeNewFlags)

    def remove (self, it, removeNewFlags = True):
        """Removes a specific item in the tree. This does not remove the top-entries.
        
        @param it: Iterator which points to the entry we are going to remove.
        @type it: Iterator
        @param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
        @type removeNewFlags: boolean"""

        def __remove (type, cpv):
            del self.iters[type][cpv]
            try:
                del self.deps[type][cpv]
            except KeyError: # this seems to be removed due to a BlockedException - so no deps here atm ;)
                debug("Catched KeyError => %s seems not to be in self.deps. Should be no harm in normal cases.", cpv)

            for key in self.blocks[type].keys():
                if cpv in self.blocks[type][key]:
                    self.blocks[type][key].remove(cpv)

                if not self.blocks[type][key]: # list is empty -> remove the whole key
                    del self.blocks[type][key]
            
            if removeNewFlags: # remove the changed flags
                flags.remove_new_use_flags(cpv)
                flags.remove_new_masked(cpv)
                flags.remove_new_testing(cpv)
        
        if self.tree.iter_has_parent(it):
            cpv = self.tree.get_value(it, self.tree.get_cpv_column())
            if self.tree.is_in_emerge(it): # Emerge
                
                __remove("install", cpv)

                try:
                    self.mergequeue.remove(cpv)
                except ValueError: # this is a dependency - ignore
                    try:
                        self.oneshotmerge.remove(cpv)
                    except ValueError:
                        debug("Catched ValueError => %s seems not to be in merge-queue. This probably means it is a dependency.", cpv)
            
            elif self.tree.is_in_unmerge(it): # in Unmerge
                try:
                    del self.iters["uninstall"][cpv]
                except KeyError as e: # this is just for debugging
                    error("'%s' not in self.iters[\"uninstall\"] for some reason", cpv)
                    debug("self.iters: %s", self.iters)
                    raise

                self.unmergequeue.remove(cpv)
            
            elif self.tree.is_in_update(it):
                __remove("update", cpv)

        self.tree.remove(it)

    def is_empty (self):
        """Checks whether the current queue is empty and not working. Therefore it looks, whether the queues are empty,
        and the process is not running.

        @returns: True if everything is empty and the process is not running.
        @rtype: bool"""

        return not (self.process or any(map(len, self.iters.values())))
