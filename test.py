from __future__ import with_statement

from portato import _sub_start
_sub_start()

from portato.eix import EixReader
from portato.backend import system

def run():
    with EixReader("/var/cache/eix") as eix:
        for c in eix.categories:
            c.name
            for p in c.packages:
                p.name

def run2():
    for i in system.find_packages(with_version = False):
        cat, pkg = i.split("/")

def run3():
    inst = system.find_packages(pkgSet = system.SET_INSTALLED, with_version = False)

    for i in range(200):
        "bla" in inst

def run4():
    inst = set(system.find_packages(pkgSet = system.SET_INSTALLED, with_version = False))
    for i in range(200):
        "bla" in inst
