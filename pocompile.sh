#!/bin/bash
# Helper script to compile all .po files in the i18n directroy into .mo files.

cd i18n

eme=""
if [[ "$1" == "-emerge" ]]; then
	eme="y"
	shift
fi

if [[ $# > 0 ]]; then
	langs="$@"
else
	langs="$(ls *.po | sed 's/\.po//g')"
fi

for lang in $langs; do
	item=${lang}.po

	if [[ -f $item ]]; then
		echo "Creating translation file for ${lang}."

		if [[ -n eme ]]; then
			mkdir mo -p
			msgfmt ${item} -o mo/${lang}.mo
		else
			mkdir ${lang}/LC_MESSAGES -p
			msgfmt ${item} -o ${lang}/LC_MESSAGES/portato.mo
		fi
	fi
done
