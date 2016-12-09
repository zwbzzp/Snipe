#!/bin/bash
# Copyright 2016 Vinzor Co,Ltd.
# vinzor license management system deployment

set -e
set -o pipefail

CURRENT_DIR="$(cd "$(dirname "$0")"; pwd)"
LOCALRC=$CURRENT_DIR/localrc
SOURCE_TYPE=${SOURCE_TYPE:-local}

# Display welcome
echo 
echo "########################################################################"
echo "Welcome to Vinzor license management system deployment"
echo "########################################################################"

# Load configuration ###########################################################
echo && echo "Load configurations"
source "$LOCALRC"

# check system #################################################################
echo && echo "Check distribution"
if ! which lsb_release > /dev/null ; then
    echo "Unknown linux distribution" && exit 1
fi

if [ "$(lsb_release -is)" != "Ubuntu" ]; then
    echo "Only support ubuntu" && exit 1
fi

if [ "$(lsb_release -rs)" \< 14.04 ]; then
    echo "Only support ubuntu 14.04 and later" && exit 1
fi

if [ $(id -u) -ne 0 ]; then
    echo "Need to run as root" && exit 1
fi

TMP_SOURCES_LIST=$(mktemp)
cat $CURRENT_DIR/tools/sources-$SOURCE_TYPE-$(lsb_release -rs).list > "$TMP_SOURCES_LIST"
sed -e "s|%PACKAGE_DIR%|$CURRENT_DIR/archives/$(lsb_release -rs)/ubuntu|" \
    -i "$TMP_SOURCES_LIST"
export APT_OPTIONS="-o Dir::Etc::SourceList=$TMP_SOURCES_LIST
 -o Dir::Etc::SourceParts=$CURRENT_DIR/tools/sources.list.d"

apt-get $APT_OPTIONS update


progress_count=0
function show_progress() {
    message=$1
    progress=$2
    [ -z "$progress" ] && progress=100
    b=""
    for ((i = 0; i < progress; i+=2)); do b='#'$b ; done
    ((row = 1 + progress_count + progress_count))
    ((progress_count += 1))
    #tput cup $row 0
    echo $message
    printf "Total:[%-50s]%d%%\n" $b $progress
}

clear || :

mkdir -p /var/log/vinzor/license
rm -rf /var/log/vinzor/license/*
logdir=/var/log/vinzor/license

function exec_sh() {
    script=$1
    bash "${CURRENT_DIR}/lib/${script}" 2>&1 | tee -a "${logdir}/${script}.log" | tee -a "${logdir}/all.log" >> /dev/null
}

# common component #############################################################
echo "------------------ Installing system ------------------"
show_progress "Installing crudini" 10               && exec_sh crudini.sh
show_progress "Installing mysql" 30                 && exec_sh mysql.sh
show_progress "Installing nginx" 50                 && exec_sh nginx.sh
#show_progress "Installing rabbitmq" 60              && exec_sh rabbitmq.sh
show_progress "Installing license management system" 80     && exec_sh project.sh

# remove env ###################################################################
rm -rf "$TMP_SOURCES_LIST"

show_progress "Done" 100

echo Bye!

