#!/bin/sh

cflags=$(python -c "from portato.backend import system; print system.get_global_settings('CFLAGS')")

find -name "*.so" -print0 | xargs -0 rm -f
find -name "*.c" -print0 | xargs -0 rm -f

CFLAGS=$cflags python setup.py build_ext -i

rm -rf build
