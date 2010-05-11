#!/bin/bash

fail ()
{
    echo ERROR: $1
    exit $2
}

replace_by ()
{
    echo ">>> ** Replace $1 by $2"

    sed -i -e "s#^\($1\s*=\s*\).*#\1$2#" portato/constants.py \
        || fail "Failure replacing $1" 1
}

ver=$(git describe --tags | sed -e "s/^v//")
name=portato-$ver

echo ">>> Cloning..."
git clone . $name || fail "Cloning" 1

pushd $name > /dev/null

echo ">>> Compiling Cython sources"
find -name '*.pyx' | xargs cython || fail "Cython" 1

echo ">>> Patching constants.py"
replace_by VERSION "'$ver'"
replace_by ROOT_DIR "'/'"
replace_by LOCALE_DIR "pjoin(ROOT_DIR, '/usr/share/locale')"
replace_by TEMPLATE_DIR "pjoin(ROOT_DIR, DATA_DIR, 'templates')"
replace_by DATA_DIR "'/usr/share/portato/'"

echo ">>> Patching setup.py."
sed -i -e "s/^.*#!REMOVE\$//" setup.py || fail "Failure removing lines" 1
sed -i -e "s/^\(\s*\)#!INSERT \(.*\)/\1\2/" setup.py || fail "Failure inserting lines" 1

echo ">>> Creating README"
cat << EOF > README
This package is intended solely for being used system-wide (normally installed via Portage).

If you want to have a packed version (for whatever reason), please use one of the following sources:

* Packed snapshot: http://git.necoro.eu/portato.git/snapshot/portato-v${ver}.tar.gz
* Git Tree: git clone git://necoro.eu/portato.git --> cd portato --> git checkout -b v${ver} v${ver}

In both cases you should read: http://necoro.eu/portato/development

EOF

popd > /dev/null

echo ">>> Packing"
tar -zcvf ${name}.tar.gz $name --exclude ".git*" || fail "Packing" 1

echo ">>> Removing temp dir"
rm -rf $name || fail "Removing" 1
