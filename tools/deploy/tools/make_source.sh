#!/bin/bash
# Make local openstack software repository

set -e
set -o pipefail

if ! which lsb_release > /dev/null ; then
    echo "Unknown linux distribution" && exit 1
fi

if [ "$(lsb_release -is)" != "Ubuntu" ]; then
    echo "Only support ubuntu" && exit 1
fi

if [ "$(lsb_release -rs)" \< 14.04 ]; then
    echo "Only support ubuntu 14.04 and later" && exit 1
fi

CURRENT_DIR=$(cd "$(dirname "$0")"; pwd)
OS_VERSION=$(lsb_release -rs)
mkdir -p "$CURRENT_DIR"/../archives/"$OS_VERSION"
ARCHIVES_DIR=$(cd "$CURRENT_DIR"/../archives/"$OS_VERSION"; pwd)

########################################
# Make ubuntu
########################################
mkdir -p "$ARCHIVES_DIR/ubuntu"
UBUNTU_ARCHIVES=$(cd "$ARCHIVES_DIR/ubuntu"; pwd)
APT_OPTIONS="-o Dir::Etc::SourceList=$CURRENT_DIR/sources-aliyun-$(lsb_release -rs).list
 -o Dir::Etc::SourceParts=$CURRENT_DIR/sources.list.d
 -o Dir::Cache::Archives=$UBUNTU_ARCHIVES"

# clean the system
sudo apt-get -y --force-yes purge dpkg-dev python3-pip git || :
sudo apt-get -y --force-yes --purge autoremove

sudo apt-get $APT_OPTIONS --force-yes update

sudo apt-get $APT_OPTIONS -d -y --force-yes install python3 python3-pip \
    mysql-server rabbitmq-server crudini nginx git debconf-utils dpkg-dev \
    apache2 apache2-utils libapache2-mod-proxy-uwsgi

# install some packages
sudo apt-get $APT_OPTIONS -y --force-yes install dpkg-dev python3-pip git
sudo pip3 install --upgrade setuptools

# auto clean old package
sudo apt-get $APT_OPTIONS autoclean

$( cd "${UBUNTU_ARCHIVES}" ; dpkg-scanpackages -m . /dev/null | gzip>./Packages.gz )


########################################
# Make project
########################################
sudo rm -rf "${ARCHIVES_DIR}/project"
mkdir -p "${ARCHIVES_DIR}/project"
PROJECT_DIR=$(cd "${ARCHIVES_DIR}/project"; pwd)
REPO_URL="ssh://git@172.18.231.4:2222/vinzor/phoenix.git"
REPO_KEY=${REPO_KEY:-${CURRENT_DIR}/phoenix}
REPO_BRANCH=${REPO_BRANCH:-"develop"}

chmod 400 "$REPO_KEY"

ssh-agent bash -c "ssh-add \"$REPO_KEY\"; git clone --depth 1 -b \"$REPO_BRANCH\" \"$REPO_URL\" \"$PROJECT_DIR\""

# compile
for pyfile in $(find "$PROJECT_DIR" -type f -name '*.py'); do
    python3 -OO -m py_compile "$pyfile"
    if !(echo "$pyfile" | grep manage.py > /dev/null); then
        rm -f pyfile
    fi
done


########################################
# Make python
########################################
mkdir -p "${ARCHIVES_DIR}/python"
PYTHON_ARCHIVES=$(cd "${ARCHIVES_DIR}/python"; pwd)
rm -rf "${PYTHON_ARCHIVES}"/*
pip3 install --download "${PYTHON_ARCHIVES}" uwsgi
pip3 install --download "${PYTHON_ARCHIVES}" virtualenv
pip3 install --download "${PYTHON_ARCHIVES}" setuptools
pip3 install --download "${PYTHON_ARCHIVES}" pbr
pip3 install --download "${PYTHON_ARCHIVES}" -r "$PROJECT_DIR/requirements.txt"


########################################
# Clean up
########################################

# clean
sudo apt-get -y --force-yes purge dpkg-dev python3-pip git
sudo apt-get -y --force-yes --purge autoremove

if (dpkg -l | grep ^rc > /dev/null); then
    dpkg -l | grep ^rc | awk '{print $2}' | sudo xargs dpkg -P
fi
