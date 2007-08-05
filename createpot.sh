#!/bin/sh

# Create the .pot file
# Thanks to porthole for inspiration ;)

files=$(find -name "*.py")
xgettext -k_ -kN_ -L glade -o i18n/messages.pot  portato/gui/templates/portato.glade
xgettext -k_ -kN_ -j --from-code=UTF-8 -o i18n/messages.pot $files

