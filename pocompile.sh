#!/bin/sh
# Helper script to compile all .po files in the i18n directroy into .mo files.

cd i18n

eme=""
if [ "$1" == "-emerge" ]; then
	eme="y"
	shift
fi

if [ $# -gt 0 ]; then
	langs="$@"
else
	langs="$(ls *.po | sed 's/\.po//g')"
fi

for LANG in $langs; do
	ITEM=${LANG}.po

	if [ -f $ITEM ]; then
		echo "Creating translation file for ${LANG}."

		if [ "$eme"x == "yx" ]; then
			mkdir mo -p
			msgfmt ${ITEM} -o mo/${LANG}.mo
		else
			mkdir ${LANG}/LC_MESSAGES -p
			msgfmt ${ITEM} -o ${LANG}/LC_MESSAGES/portato.mo
		fi
	fi
done
