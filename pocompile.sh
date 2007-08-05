#!/bin/sh
# Helper script to compile all .po files in the i18n directroy into .mo files.

# Copied from porthole :)
cd i18n
for ITEM in *.po; do
	ITEM2=${ITEM/.po/}
	LANG=${ITEM2/_??/}
	mkdir ${LANG}/LC_MESSAGES -p

	if [ $1 == "-emerge" ]; then
		msgfmt ${ITEM} -o portato.${LANG}
	else
		msgfmt ${ITEM} -o ${LANG}/LC_MESSAGES/portato.mo
	fi
done
