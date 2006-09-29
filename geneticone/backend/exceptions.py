#
# File: geneticone/backend/exceptions.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 Necoro d.M.
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by Necoro d.M. <necoro@necoro.net>

class BlockedException (Exception):
	"""An exception marking, that some package is blocking another one."""
	pass

class PackageNotFoundException (Exception):
	"""An exception marking that a package could not be found."""
	pass

class DependencyCalcError (Exception):
	"""An error occured during dependency calculation."""
	pass
