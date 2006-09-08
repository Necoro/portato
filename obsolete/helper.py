#!/usr/bin/python

from geneticone import helper

"""Some obsolete functions from geneticone.helper."""

def old_export_to_dictionaries (list_of_packages):
	'''DEPRECATED:
	Exports some of the intrinsic data of a list of Package objects to a list of dictionaries.
	This is meant to transmit data back to the genetic-client, just by eval()-uating the output.'''
	dictionaries=[]
	keys=['name','version','category','cpv','runtime_deps','compiletime_deps','postmerge_deps','is_installed', 'is_overlay', 'is_masked','mask_status', 'package_path', 'size','use_flags_when_installed','all_useflags','set_useflags']
	package_methods=['get_name','get_version','get_category','get_cpv','get_runtime_deps', 'get_compiletime_deps','get_postmerge_deps','is_installed','is_overlay','is_masked','get_mask_status','get_package_path','size','get_use_flags','get_all_useflags','get_set_useflags']
	
	for item in list_of_packages:
		dictionaries.append({})
		for key,method in zip(keys,package_methods):
			try:
				dictionaries[-1][key]=eval('item.'+method+'()')
			except AttributeError: #this may happen if, for example, package is not installed and I look for the path...
				dictionaries[-1][key]=None
	return dictionaries

def export_to_dictionaries (packages):
	'''Exports some of the intrinsic data of a list of Package objects to a list of dictionaries.
	This is meant to transmit data back to the genetic-client, just by eval()-uating the output.'''
	dictionaries=[]

	for item in packages:
		dictionaries.append({})
		for method in dir(item):
			if (method.startswith('get_') or method.startswith('is_'))\
					and method != 'get_dependants': # bug in gentoolkit.Package.get_dependants --> see bug #137783
				key = method[method.index('_')+1:] # the key is everything after the first underscore
				try:
					dictionaries[-1][key] = eval("item."+method+"()")
				except AttributeError: # this may happen if, for example, package is not installed and I look for the path...
					dictionaries[-1][key] = None
				except TypeError:
					pass # this method takes an argument - ignore it
				except NotImplementedError:
					pass # this method is not implemented - ignore
				except "Not implemented yet!":
					pass
	return dictionaries
