#!/bin/sh

# Create the .pot file
# Thanks to porthole for inspiration ;)

xgettext -k_ -kN_ -L glade -o i18n/messages.pot $(find -name "*.glade")
xgettext -k_ -kN_ -j --from-code=UTF-8 -o i18n/messages.pot $(find -name "*.py")

