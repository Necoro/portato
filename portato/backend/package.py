# -*- coding: utf-8 -*-
#
# File: portato/backend/package.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from ..helper import debug, paren_reduce
from ..dependency import DependencyTree

from . import _Package, system, flags

class Package (_Package):
    """This is a class abstracting a normal package which can be installed."""

    def __init__ (self, cpv):
        """Constructor.

        @param cpv: The cpv which describes the package to create.
        @type cpv: string (cat/pkg-ver)"""

        self._cpv = cpv

    def __repr__ (self):
        return "<Package '%s' @0x%x>" % (self._cpv, id(self))

    __str__ = __repr__
    
    #
    # implemented
    #
    
    def set_testing(self, enable = True):
        """Sets the actual testing status of the package.
        
        @param enable: if True it is masked as stable; if False it is marked as testing
        @type enable: boolean"""
        
        flags.set_testing(self, enable)

    def remove_new_testing(self):
        """Removes possible changed testing status."""
        
        flags.remove_new_testing(self.get_cpv())

    def set_masked (self, masking = False):
        """Sets the masking status of the package.
    
        @param masking: if True: mask it; if False: unmask it
        @type masking: boolean"""
        
        flags.set_masked(self, masked = masking)

    def remove_new_masked (self):
        """Removes possible changed masking status."""
        
        flags.remove_new_masked(self.get_cpv())

    def is_locally_masked (self):
        """Checks whether the package is masked by the user.

        @returns: True if masked by the user; False if not
        @rtype: bool"""

        return flags.is_locally_masked(self)

    def get_new_use_flags (self):
        """Returns a list of the new useflags, i.e. these flags which are not written to the portage-system yet.

        @returns: list of flags or []
        @rtype: string[]"""

        return flags.get_new_use_flags(self)

    def get_actual_use_flags (self):
        """This returns all currently set use-flags including the new ones.

        @return: list of flags
        @rtype: string[]"""

        i_flags = self.get_global_settings("USE", installed = False).split()
        m_flags = system.get_global_settings("USE").split()
        for f in self.get_new_use_flags():
            removed = False

            if f[0] == "~":
                f = f[1:]
                removed = True

            invf = flags.invert_use_flag(f)
            
            if f[0] == '-':
                if invf in i_flags and not (removed and invf in m_flags):
                    i_flags.remove(invf)
                
            elif f not in i_flags:
                if not (removed and invf in m_flags):
                    i_flags.append(f)

        return i_flags

    def set_use_flag (self, flag):
        """Set a use-flag.

        @param flag: the flag to set
        @type flag: string"""
        
        flags.set_use_flag(self, flag)

    def remove_new_use_flags (self):
        """Remove all the new use-flags."""
        
        flags.remove_new_use_flags(self)

    def use_expanded (self, flag, suggest = None):
        """Tests whether a useflag is an expanded one. If it is, this method returns the USE_EXPAND-value.

        @param flag: the flag to check
        @type flag: string
        @param suggest: try this suggestion first
        @type suggest: string
        @returns: USE_EXPAND-value on success
        @rtype: string or None"""

        if suggest is not None:
            if flag.startswith(suggest.lower()):
                return suggest

        for exp in self.get_global_settings("USE_EXPAND").split():
            lexp = exp.lower()
            if flag.startswith(lexp):
                return exp

        return None

    def get_cpv(self):
        """Returns full Category/Package-Version string.
        
        @returns: the cpv
        @rtype: string"""
        
        return self._cpv

    def get_cp (self):
        """Returns the cp-string.
        
        @returns: category/package.
        @rtype: string"""
        
        return self.get_category()+"/"+self.get_name()

    def get_slot_cp (self):
        """Returns the current cp followed by a colon and the slot-number.
        
        @returns: cp:slot
        @rtype: string"""

        return ("%s:%s" % (self.get_cp(), self.get_package_settings("SLOT")))

    def get_package_path(self):
        """Returns the path to where the ChangeLog, Manifest, .ebuild files reside.
        
        @returns: path to the package files
        @rtype: string"""
        
        p = self.get_ebuild_path()
        sp = p.split("/")
        if sp:
            return "/".join(sp[:-1])

    def get_dependencies (self):
        """
        Returns the tree of dependencies that this package needs.

        @rtype: L{DependencyTree}
        """
        deps = " ".join(map(self.get_package_settings, ("RDEPEND", "PDEPEND", "DEPEND")))
        deps = paren_reduce(deps)
        
        tree = DependencyTree()
        tree.parse(deps)

        return tree

    #
    # Not implemented
    #

    def get_name(self):
        """Returns base name of package, no category nor version.
        
        @returns: base-name
        @rtype: string"""
        
        raise NotImplementedError

    def get_version(self):
        """Returns version of package, with (optional) revision number.
        
        @returns: version-rev
        @rtype: string"""
        
        raise NotImplementedError

    def get_category(self):
        """Returns category of package.
        
        @returns: category
        @rtype: string"""
        
        raise NotImplementedError

    def is_installed(self):
        """Returns true if this package is installed (merged).
        @rtype: boolean"""

        raise NotImplementedError

    def is_in_overlay(self):
        """Returns true if the package is in an overlay.
        @rtype: boolean"""

        raise NotImplementedError

    def get_overlay_path(self):
        """Returns the path to the current overlay.
        @rtype: string"""

        raise NotImplementedError
        
    def is_in_system (self):
        """Returns False if the package could not be found in the portage system.

        @return: True if in portage system; else False
        @rtype: boolean"""

        raise NotImplementedError

    def is_missing_keyword(self):
        """Returns True if the package is missing the needed keyword.
        
        @return: True if keyword is missing; else False
        @rtype: boolean"""

        raise NotImplementedError
        
    def is_testing(self, use_keywords = True):
        """Checks whether a package is marked as testing.
        
        @param use_keywords: Controls whether possible keywords are taken into account or not.
        @type use_keywords: boolean
        @returns: True if the package is marked as testing; else False.
        @rtype: boolean"""

        raise NotImplementedError

    def is_masked (self, use_changed = True):
        """Returns True if either masked by package.mask or by profile.
        
        @param use_changed: Controls, whether changes applied to masking keywords are taken into account.
        @type use_changed: boolean
        @returns: True if masked / False otherwise
        @rtype: boolean"""

        raise NotImplementedError

    def get_masking_reason (self):
        """Returns the reason for masking the package. If this is not possible for the system, return None.

        @returns: the reason for masking the package
        @rtype: string"""
        
    def get_iuse_flags (self, installed = False, removeForced = True):
        """Returns a list of _all_ useflags for this package, i.e. all useflags you can set for this package.
        
        @param installed: do not take the ones stated in the ebuild, but the ones it has been installed with
        @type installed: boolean
        @param removeForced: remove forced flags (i.e. usemask / useforce) from the iuse flags as they cannot be set from the user
        @type removeForced: boolean

        @returns: list of use-flags
        @rtype: string[]"""

        raise NotImplementedError

    def get_matched_dep_packages (self, depvar):
        """This function looks for all dependencies which are resolved. In normal case it makes only sense for installed packages, but should work for uninstalled ones too.

        @param depvar: the dependency variables (RDEPEND, PDEPEND, DEPEND) to use
        @type depvar: string[]
        
        @returns: unique list of dependencies resolved (with elements like "<=net-im/foobar-1.2.3")
        @rtype: string[]

        @raises portato.DependencyCalcError: when an error occured during executing portage.dep_check()"""

        raise NotImplementedError
        
    def get_dep_packages (self, depvar = ["RDEPEND", "PDEPEND", "DEPEND"], with_criterions = False):
        """Returns a cpv-list of packages on which this package depends and which have not been installed yet. This does not check the dependencies in a recursive manner.

        @param depvar: the dependency variables (RDEPEND, PDEPEND, DEPEND) to use
        @type depvar: string[]
        @param with_criterions: return also the criterions
        @type with_criterions: boolean
        
        @returns: list of cpvs on which the package depend (and if wanted also the criterions)
        @rtype: string[] or (string, string)[]

        @raises portato.BlockedException: when a package in the dependency-list is blocked by an installed one
        @raises portato.PackageNotFoundException: when a package in the dependency list could not be found in the system
        @raises portato.DependencyCalcError: when an error occured during executing portage.dep_check()"""

        raise NotImplementedError

    def get_global_settings(self, key, installed = True):
        """Returns the value of a global setting, i.e. ARCH, USE, ROOT, DISTDIR etc.
        
        @param key: the setting to return
        @type key: string
        @param installed: get the installed settings or the ebuild settings
        @type installed: boolean
        @returns: the value of this setting
        @rtype: string"""

        raise NotImplementedError

    def get_ebuild_path(self):
        """Returns the complete path to the .ebuild file.
        
        @rtype: string"""

        raise NotImplementedError

    def get_files (self):
        """
        Returns an iterator over the installed files of a package.
        If the package is not installed, the iterator should be "empty".

        @returns: the installed files
        @rtype: string<iterator>
        """

        raise NotImplementedError

    def get_package_settings(self, var, installed = True):
        """Returns a package specific setting, such as DESCRIPTION, SRC_URI, IUSE ...
        
        @param var: the setting to get
        @type var: string
        @param installed: take the vartree or the porttree
        @type installed: boolean
        
        @returns: the value of the setting
        @rtype: string"""

        raise NotImplementedError

    def get_installed_use_flags(self):
        """Returns _all_ (not only the package-specific) useflags which were set at the installation time of the package.
        
        @returns: list of use flags
        @rtype: string[]"""
        
        raise NotImplementedError

    def compare_version(self, other):
        """Compares this package's version to another's CPV; returns -1, 0, 1.
        
        @param other: the other package
        @type other: Package
        @returns: -1, 0 or 1
        @rtype: int"""

        raise NotImplementedError

    def matches (self, criterion):
        """This checks, whether this package matches a specific versioning criterion - e.g.: "<=net-im/foobar-1.2".
        
        @param criterion: the criterion to match against
        @type criterion: string
        @returns: True if matches; False if not
        @rtype: boolean"""

        raise NotImplementedError
