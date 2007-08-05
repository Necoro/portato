#!/bin/sh
# Helper script to compile all .po files in the i18n directroy into .mo files.

# Copied from porthole :)
cd i18n
for ITEM in *.po; do
	LANG=${ITEM/.po/}

	if [ "$1" == "-emerge" ]; then
		mkdir mo -p
		msgfmt ${ITEM} -o mo/${LANG}.mo
	else
		mkdir ${LANG}/LC_MESSAGES -p
		msgfmt ${ITEM} -o ${LANG}/LC_MESSAGES/portato.mo
	fi
done
