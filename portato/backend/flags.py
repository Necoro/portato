# -*- coding: utf-8 -*-
#
# File: portato/backend/flags.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

import os
import os.path
import itertools as itt
from subprocess import Popen, PIPE # needed for grep

from . import system, is_package
from ..helper import debug, error, unique_array

CONFIG = {
        "usefile" : "portato",
        "maskfile" : "portato",
        "testingfile" : "portato",
        "usePerVersion" : True,
        "maskPerVersion" : True,
        "testingPerVersion" : True
        }

class Constants:

    def __init__ (self):
        self.clear()
    
    def clear (self):
        self._use_path = None
        self._mask_path = None
        self._unmask_path = None
        self._testing_path = None
        self._use_path_is_dir = None
        self._mask_path_is_dir = None
        self._unmask_path_is_dir = None
        self._testing_path_is_dir = None

    def __get (self, name, path):
        if self.__dict__[name] is None:
            self.__dict__[name] = os.path.join(system.get_config_path(), path)

        return self.__dict__[name]

    def __is_dir(self, path):
        name = "_" + path + "_is_dir"
        if self.__dict__[name] is None:
            self.__dict__[name] = os.path.isdir(self.__class__.__dict__[path](self))
        return self.__dict__[name]
    
    def use_path (self):
        return self.__get("_use_path", "package.use")

    def use_path_is_dir (self):
        return self.__is_dir("use_path")

    def mask_path (self):
        return self.__get("_mask_path", "package.mask")

    def mask_path_is_dir (self):
        return self.__is_dir("mask_path")

    def unmask_path (self):
        return self.__get("_unmask_path", "package.unmask")

    def unmask_path_is_dir (self):
        return self.__is_dir("unmask_path")

    def testing_path (self):
        return self.__get("_testing_path", "package.keywords")

    def testing_path_is_dir (self):
        return self.__is_dir("testing_path")

CONST = Constants()

### GENERAL PART ###

def grep (pkg, path):
    """Grep runs "egrep" on a given path and looks for occurences of a given package.
    @param pkg: the package
    @type pkg: string (cpv) or L{backend.Package}-object
    @param path: path to look in
    @type path: string
    
    @returns: occurences of pkg in the format: "file:line-no:complete_line_found"
    @rtype: string"""

    if not is_package(pkg):
        pkg = system.new_package(pkg) # assume it is a cpv or a gentoolkit.Package

    if os.path.exists(path):
        command = "egrep -x -n -r -H '^[<>!=~]{0,2}%s(-[0-9].*)?[[:space:]]?.*$' %s" # %s is replaced in the next line ;)
        return Popen((command % (pkg.get_cp(), path)), shell = True, stdout = PIPE).communicate()[0].splitlines()
    else:
        return []

def get_data(pkg, path):
    """This splits up the data of L{grep} and builds tuples in the format (file,line,criterion,list_of_flags).
    @param pkg: package to find
    @type pkg: string (cpv) or L{backend.Package}-object
    @param path: path to look in
    @type path: string
    
    @returns: a list of tuples in the form (file,line,criterion,list_of_flags)
    @rtype: (string,string,string,string[])[]"""
    
    flags = []

    for line in grep(pkg, path):
        file, line, fl = line.split(":") # get file, line and flag-list
        fl = fl.split()
        crit = fl[0]
        fl = fl[1:]
        
        # stop after first comment
        nc = itt.takewhile(lambda x: x[0] != "#", fl)
        flags.append((file, line, crit, list(nc)))

    return flags

def set_config (cfg):
    """This function sets the CONFIG-variable for the whole module. Use this instead of modifying L{CONFIG} directly.
    @param cfg: a dictionary with at least all the keys of the CONFIG-var
    @type cfg: dict
    @raises KeyError: if a keyword is missing in the new cfg"""

    for i in CONFIG.keys():
        if not i in cfg:
            raise KeyError, "Missing keyword in config: "+i

    for i in CONFIG:
        CONFIG[i] = cfg[i]

def generate_path (cpv, exp):
    """Generates the correct path out of given wildcards. 
    These wildcards can be:
        - $(cat) : category
        - $(cat-1): first part of the category (e.g. "app")
        - $(cat-2): second part of the category
        - $(pkg) : name of the package
        - $(version) : version of the package
    
    @param cpv: the cpv of the current package
    @type cpv: string (cat/pkg-ver)
    @param exp: the expression to render the path from
    @type exp: string
    @returns: rendered path
    @rtype string"""

    if exp.find("$(") != -1:
        cat, pkg, ver, rev = system.split_cpv(cpv)
        if rev != "r0":
            ver = "%s-%s" % (ver, rev)
        exp = exp.replace("$(cat)",cat).\
                replace("$(pkg)",pkg).\
                replace("$(cat-1)",cat.split("-")[0]).\
                replace("$(cat-2)",cat.split("-")[1]).\
                replace("$(version)",ver)
    return exp

### USE FLAG PART ###
useFlags = {} # useFlags in the file
newUseFlags = {} # useFlags as we want them to be: format: cpv -> [(file, line, useflag, (true if removed from list / false if added))]

def invert_use_flag (flag):
    """Invertes a flag.

        >>> invert_use_flag("foo")
        -foo
        >>> invert_use_flag("-bar")
        bar

    @param flag: the flag
    @type flag: string
    @returns: inverted flag
    @rtype: string
    """
    
    if flag[0] == "-":
        return flag[1:]
    else:
        return "-"+flag

def sort_use_flag_list (flaglist):
    """
    Sorts a list of useflags. If a use flag starts with "+" or "-" this one is ignored for the matter of sorting.
    This functions sorts the list itself - thus does not create a new one. But for convenience it returns the list too.

    @param flaglist: the list of useflags
    @type flaglist: string[]

    @returns: the sorted list (Note: it is the same as the one passed in)
    @rtype: string[]
    """
    
    def flag_key (flag):
            if flag[0] in "+-":
                return flag[1:]
            else:
                return flag
    
    flaglist.sort(key = flag_key)
    return flaglist

def filter_defaults (flaglist):
    """
    Removes "+" and "-" from IUSE defaults.

    @param flaglist: the list of useflags
    @type flaglist: string<iterator>

    @returns: the "cleaned" list
    @rtype: string<iterator>
    """

    for flag in flaglist:
        if flag[0] in "+-":
            yield flag[1:]
        else:
            yield flag

def set_use_flag (pkg, flag):
    """Sets the useflag for a given package.
    
    @param pkg: the package
    @type pkg: string (cpv) or L{backend.Package}-object
    @param flag: the flag to set
    @type flag: string"""

    global useFlags, newUseFlags

    if not is_package(pkg):
        pkg = system.new_package(pkg) # assume cpv or gentoolkit.Package

    cpv = pkg.get_cpv()
    invFlag = invert_use_flag(flag)
    
    # if not saved in useFlags, get it by calling get_data() which calls grep()
    data = None
    if not cpv in useFlags:
        data = get_data(pkg, CONST.use_path())
        useFlags[cpv] = data
    else:
        data = useFlags[cpv]

    if not cpv in newUseFlags:
        newUseFlags[cpv] = []

    debug("data: %s", str(data))
    # add a useflag / delete one
    added = False
    for file, line, crit, flags in data:
        if pkg.matches(crit):
            # we have the inverted flag in the uselist/newuselist --> delete it
            if invFlag in flags or (file, line, invFlag, False) in newUseFlags[cpv] or (file, line, flag, True) in newUseFlags[cpv]:
                if added: del newUseFlags[cpv][-1] # we currently added it as an extra option - delete it
                added = True
                jumpOut = False
                for t in ((file, line, invFlag, False),(file, line, flag, True)):
                    if t in newUseFlags[cpv]:
                        newUseFlags[cpv].remove(t)
                        jumpOut = True
                        # break # don't break as both cases can be valid (see below)
                if not jumpOut:
                    newUseFlags[cpv].append((file, line, invFlag, True))
                    
                    # we removed the inverted from package.use - but it is still enabled somewhere else
                    # so set it explicitly here
                    if invFlag in pkg.get_actual_use_flags():
                        newUseFlags[cpv].append((file, line, flag, False))
                break
            
            # we want to duplicate the flag --> ignore
            elif flag in flags:
                added = True # emulate adding
                break

            # add as an extra flag
            else:
                if not added: newUseFlags[cpv].append((file, line, flag, False))
                added = True
    
    # create a new line
    if not added:
        path = CONST.use_path()
        if CONST.use_path_is_dir():
            path = os.path.join(CONST.use_path(), generate_path(cpv, CONFIG["usefile"]))
        try:
            newUseFlags[cpv].remove((path, -1, invFlag, False))
        except ValueError: # not in UseFlags
            newUseFlags[cpv].append((path, -1, flag, False))

    newUseFlags[cpv] = unique_array(newUseFlags[cpv])
    debug("newUseFlags: %s", str(newUseFlags))

def remove_new_use_flags (cpv):
    """Removes all new use-flags for a specific package.
    
    @param cpv: the package for which to remove the flags
    @type cpv: string (cpv) or L{backend.Package}-object"""
    
    if is_package(cpv):
        cpv = cpv.get_cpv()
    
    try:
        del newUseFlags[cpv]
    except KeyError:
        pass

def get_new_use_flags (cpv):
    """Gets all the new use-flags for a specific package.
    
    @param cpv: the package from which to get the flags
    @type cpv: string (cpv) or L{backend.Package}-object
    @returns: list of flags
    @rtype: string[]"""
    
    if is_package(cpv):
        cpv = cpv.get_cpv()

    list2return = set()
    try:
        for file, line, flag, remove in newUseFlags[cpv]:
            if remove:
                list2return.add("~"+invert_use_flag(flag))
            else:
                list2return.add(flag)
    except KeyError:
        pass

    return list(list2return)

def write_use_flags ():
    """This writes our changed useflags into the file."""
    global newUseFlags, useFlags

    def insert (flag, list):
        """Shortcut for inserting a new flag right after the package-name."""
        list.insert(1,flag)
    
    def remove (flag, list):
        """Removes a flag."""
        try:
            list.remove(flag)
        except ValueError: # flag is given as flag\n
            list.remove(flag+"\n")
            list.append("\n") #re-insert the newline

        # no more flags there - comment it out
        if len(list) == 1 or list[1][0] in ("#","\n"):
            list[0] = "#"+list[0]
            insert("#removed by portato#",list)

    file_cache = {} # cache for having to read the file only once: name->[lines]
    for cpv in newUseFlags:
        flagsToAdd = [] # this is used for collecting the flags to be inserted in a _new_ line

        newUseFlags[cpv].sort(key = lambda x: x[3]) # now the flags are sorted in a manner, that removal comes after appending

        for file, line, flag, delete in newUseFlags[cpv]:
            line = int(line) # it is saved as a string so far!
            # add new line
            if line == -1:
                flagsToAdd.append(flag)
            # change a line
            else:
                if not file in file_cache:
                    # read file
                    with open(file, "r") as f:
                        lines = []
                        i = 1
                        while i < line: # stop at the given line
                            lines.append(f.readline())
                            i += 1
                        l = f.readline().split(" ")
                        
                        # delete or insert
                        if delete:
                            remove(flag,l)
                        else:
                            insert(flag,l)
                        lines.append(" ".join(l))
                        
                        # read the rest
                        lines.extend(f.readlines())
                        
                        file_cache[file] = lines

                else: # in cache
                    l = file_cache[file][line-1].split(" ")
                    if delete:
                        remove(flag, l)
                    else:
                        insert(flag,l)
                    file_cache[file][line-1] = " ".join(l)

        if flagsToAdd:
        # write new lines
            msg = "\n#portato update#\n"
            if CONFIG["usePerVersion"]: # add on a per-version-base
                msg += "=%s %s\n" % (cpv, ' '.join(flagsToAdd))
            else: # add on a per-package-base
                list = system.split_cpv(cpv)
                msg += "%s/%s %s\n" % (list[0], list[1], ' '.join(flagsToAdd))
            if not file in file_cache:
                f = open(file, "a")
                f.write(msg)
                f.close()
            else:
                file_cache[file].append(msg)
    
    # write to disk
    for file in file_cache.keys():
        f = open(file, "w")
        f.writelines(file_cache[file])
        f.close()
    # reset
    useFlags = {}
    newUseFlags = {}
    system.reload_settings()

### MASKING PART ###
new_masked = {}
new_unmasked = {}

def set_masked (pkg, masked = True):
    """Sets the masking status of the package.
    
    @param pkg: the package from which to get the flags
    @type pkg: string (cpv) or L{backend.Package}-object
    @param masked: if True: mask it; if False: unmask it
    @type masked: boolean"""
    
    global new_masked, newunmasked
    
    if not is_package(pkg):
        pkg = system.new_package(pkg)

    cpv = pkg.get_cpv()

    if not cpv in new_unmasked:
        new_unmasked[cpv] = []
    if not cpv in new_masked:
        new_masked[cpv] = []

    if masked:
        link_neq = new_masked
        link_eq = new_unmasked
        path = CONST.unmask_path()
    else:
        link_neq = new_unmasked
        link_eq = new_masked
        path = CONST.mask_path()

    copy = link_eq[cpv][:]
    for file, line in copy:
        if line == "-1":
            link_eq[cpv].remove((file, line))
    
    copy = link_neq[cpv][:]
    for file, line in copy:
        if line != "-1":
            link_neq[cpv].remove((file, line))

    if masked == pkg.is_masked():
        return

    data = get_data(pkg, path)
    debug("data: %s", str(data))
    done = False
    for file, line, crit, flags in data:
        if pkg.matches(crit):
            link_eq[cpv].append((file, line))
            done = True

    if done: return

    if masked:
        is_dir = CONST.mask_path_is_dir()
        path = CONST.mask_path()
    else:
        is_dir = CONST.unmask_path_is_dir()
        path = CONST.unmask_path()

    if is_dir:
        file = os.path.join(path, generate_path(cpv, CONFIG["maskfile"]))
    else:
        file = path
    
    link_neq[cpv].append((file, "-1"))
    link_neq[cpv] = unique_array(link_neq[cpv])
    debug("new_(un)masked: %s",str(link_neq))

def remove_new_masked (cpv):
    if is_package(cpv):
        cpv = cpv.get_cpv()
    
    try:
        del new_masked[cpv]
    except KeyError:
        pass

    try:
        del new_unmasked[cpv]
    except KeyError:
        pass

def new_masking_status (cpv):
    if is_package(cpv):
        cpv = cpv.get_cpv()

    def get(list):
        ret = None
        if cpv in list and list[cpv] != []:
            for file, line in list[cpv]:
                _ret = (int(line) == -1)
                if ret is not None and _ret != ret:
                    error(_("Conflicting values for masking status: %s"), list)
                else:
                    ret = _ret
        return ret

    masked = get(new_masked)
    if masked is None:
        masked = get(new_unmasked)
        if masked is not None:
            masked = not masked # revert for new_unmasked

    if masked is not None:
        if masked: return "masked"
        else: return "unmasked"
    else:
        return None

def is_locally_masked (pkg, changes = True):

    if not is_package(pkg):
        pkg = system.new_package(pkg) # assume it is a cpv or a gentoolkit.Package

    if changes:
        if new_masking_status(pkg) == "masked": # we masked it ourselves, but did not save it yet
            # but sometimes, new_masking_status() returns "masked" if a package's unmask is removed
            # then it is masked by the system but not locally (except rarely exotic cases)
            if pkg.get_cpv() in new_unmasked:
                if new_unmasked[pkg.get_cpv()]: return False # assume that there only exists one entry for this package
                                                             # else new_masking_status should have printed an error
            return True

        if new_masking_status(pkg) == "unmasked": # we unmasked it
            return False
    
    list = get_data(pkg, CONST.mask_path())

    if not list: return False

    for file, line, crit, fl in list:
        if pkg.matches(crit):
            return True

    return False
    
def write_masked ():
    global new_unmasked, new_masked
    file_cache = {}

    def write(cpv, file, line):
        line = int(line)
        # add new line
        if line == -1:
            msg = "\n#portato update#\n"
            if CONFIG["maskPerVersion"]:
                msg += "=%s\n" % cpv
            else:
                list = system.split_cpv(cpv)
                msg += "%s/%s\n" % (list[0],list[1])
            if not file in file_cache:
                f = open(file, "a")
                f.write(msg)
                f.close()
            else:
                file_cache[file].append(msg)
        # change a line
        else:
            if not file in file_cache:
                # read file
                f = open(file, "r")
                lines = []
                i = 1
                while i < line: # stop at the given line
                    lines.append(f.readline())
                    i = i+1
                # delete
                l = f.readline()
                l = "#"+l[:-1]+" # removed by portato\n"
                lines.append(l)
                
                # read the rest
                lines.extend(f.readlines())
                
                file_cache[file] = lines
                f.close()
            else: # in cache
                l = file_cache[file][line-1]
                # delete:
                l = "#"+l[:-1]+" # removed by portato\n"
                file_cache[file][line-1] = l
    
    
    for cpv in new_masked:
        for file, line in new_masked[cpv]:
            write(cpv, file, line)
    
    for cpv in new_unmasked:
        for file, line in new_unmasked[cpv]:
            write(cpv, file, line)
    
    # write to disk
    for file in file_cache.keys():
        f = open(file, "w")
        f.writelines(file_cache[file])
        f.close()
    # reset
    new_masked = {}
    new_unmasked = {}
    system.reload_settings()

### TESTING PART ###
newTesting = {}
arch = ""

def remove_new_testing (cpv):
    if is_package(cpv):
        cpv = cpv.get_cpv()
    
    try:
        del newTesting[cpv]
    except KeyError:
        pass

def new_testing_status (cpv):
    if is_package(cpv):
        cpv = cpv.get_cpv()

    if cpv in newTesting:
        for file, line in newTesting[cpv]:
            if line == "-1": return False
            else: return True

    return None

def set_testing (pkg, enable):
    """Enables the package for installing when it is marked as testing (~ARCH).
    @param pkg: the package
    @type pkg: string (cpv) or L{backend.Package}-object
    @param enable: controls whether to enable (True) or disable (False) for test-installing
    @type enable: boolean"""

    global arch, newTesting
    if not is_package(pkg):
        pkg = system.new_package(pkg)

    arch = pkg.get_global_settings("ARCH")
    cpv = pkg.get_cpv()
    if not cpv in newTesting: 
        newTesting[cpv] = []

    for file, line in newTesting[cpv]:
        if (enable and line != "-1") or (not enable and line == "-1"):
            newTesting[cpv].remove((file, line))

    if (enable and not pkg.is_testing()) or (not enable and pkg.is_testing()):
        return

    if not enable:
        test = get_data(pkg, CONST.testing_path())
        debug("data (test): %s", str(test))
        for file, line, crit, flags in test:
            if pkg.matches(crit) and flags[0] == "~"+arch:
                newTesting[cpv].append((file, line))
    else:
        if CONST.testing_path_is_dir():
            file = os.path.join(CONST.testing_path(), generate_path(cpv, CONFIG["testingfile"]))
        else:
            file = CONST.testing_path()
        newTesting[cpv].append((file, "-1"))

    newTesting[cpv] = unique_array(newTesting[cpv])
    debug("newTesting: %s",str(newTesting))

def write_testing ():
    global arch, newTesting
    file_cache = {}

    for cpv in newTesting:
        for file, line in newTesting[cpv]:
            line = int(line)
            # add new line
            if line == -1:
                msg = "\n#portato update#\n"
                if CONFIG["testingPerVersion"]:
                    msg += "=%s ~%s\n" % (cpv, arch)
                else:
                    list = system.split_cpv(cpv)
                    msg += "%s/%s ~%s\n" % (list[0],list[1],arch)
                if not file in file_cache:
                    f = open(file, "a")
                    f.write(msg)
                    f.close()
                else:
                    file_cache[file].append(msg)
            # change a line
            else:
                if not file in file_cache:
                    # read file
                    f = open(file, "r")
                    lines = []
                    i = 1
                    while i < line: # stop at the given line
                        lines.append(f.readline())
                        i = i+1
                    # delete
                    l = f.readline()
                    l = "#"+l[:-1]+" # removed by portato\n"
                    lines.append(l)
                    
                    # read the rest
                    lines.extend(f.readlines())
                    
                    file_cache[file] = lines
                    f.close()
                else: # in cache
                    l = file_cache[file][line-1]
                    # delete:
                    l = "#"+l[:-1]+" # removed by portato\n"
                    file_cache[file][line-1] = l
    
    # write to disk
    for file in file_cache.keys():
        f = open(file, "w")
        f.writelines(file_cache[file])
        f.close()
    # reset
    newTesting = {}
    system.reload_settings()
