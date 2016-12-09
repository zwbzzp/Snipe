#!/bin/bash
# build install scripts

set -e
set -o pipefail
set -x

if ! which shc > /dev/null ; then
    echo "shc not found!"
    exit 1
fi


function ensure_dir() {
    local d=$1
    [ -d "$d" ] || mkdir -p "$d"
    (cd "$d"; pwd)
}

function compile_script() {
    local script=$1
    shc -r -f "$script"
    rm -f "$script".x.c
    mv -f "$script".x "$script"
    chmod +x "$script"
}


CUR_DIR=$(cd "$(dirname "$0")"; pwd)
BUILD_DIR=$(ensure_dir "$CUR_DIR/build")

# run.sh #######################################################################
chmod +x "$CUR_DIR/run.sh"
cp -f "$CUR_DIR/run.sh" "$BUILD_DIR"
cp -f localrc "$BUILD_DIR"

compile_script "$BUILD_DIR/run.sh"


# lib ##########################################################################
chmod +x "$CUR_DIR/lib"/*.sh
rm -rf "$BUILD_DIR/lib"
cp -aL "$CUR_DIR/lib" "$BUILD_DIR"

for script in $(find "$BUILD_DIR/lib" -type f -name '*.sh'); do
    compile_script "$script"
done


# archives #####################################################################
rsync -r "$CUR_DIR/archives" "$BUILD_DIR"


# tools ########################################################################
rsync -r "$CUR_DIR/tools" "$BUILD_DIR"


# configuration files ########################################################################
rsync -r "$CUR_DIR/conf" "$BUILD_DIR"


# others #######################################################################
#rsync -r "$CUR_DIR/cinder-all" "$BUILD_DIR"

set +x