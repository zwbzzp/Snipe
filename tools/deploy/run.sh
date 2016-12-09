#!/bin/bash
# Copyright 2016 Vinzor Co,Ltd.
# vinzor management system deployment

set -e
set -o pipefail

CURRENT_DIR="$(cd "$(dirname "$0")"; pwd)"
LOCALRC=$CURRENT_DIR/localrc
SOURCE_TYPE=${SOURCE_TYPE:-local}

# Display welcome
echo 
echo "########################################################################"
echo "Welcome to Vinzor management system deployment"
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


# configure ####################################################################
echo && echo "Installation destination:"
if [ -z "$DEST_DIR" ]; then
    select DEST_DIR in "/srv/www/vinzor" "/var/www/vinzor"; do
        [ -n "$DEST_DIR" ] && break
    done
fi
echo $DEST_DIR

# openstack
echo && echo "OpenStack Authentication URL:"
while [ -z "$OS_AUTH_URL" ]; do
    read -p "Authentication URL: " OS_AUTH_URL
done
echo $OS_AUTH_URL
# tenant
echo "OpenStack Tenant (Project):"
while [ -z "$OS_TENANT_NAME" ]; do
    read -p "Tenant: " OS_TENANT_NAME
done
echo $OS_TENANT_NAME
# user
echo "OpenStack User:"
while [ -z "$OS_USERNAME" ]; do
    read -p "User: " OS_USERNAME
done
echo $OS_USERNAME
# password
echo "OpenStack Password:"
while [ -z "$OS_PASSWORD" ]; do
    read -p "Password: " -s OS_PASSWORD
    echo
done
echo "<secret>"

# mysql
echo && echo "Mysql User:"
while [ -z "$MYSQL_USER" ]; do
    read -p "User: " MYSQL_USER
done
echo $MYSQL_USER
echo "Mysql Password:"
while [ -z "$MYSQL_PASS" ]; do
    read -p "Password: " -s MYSQL_PASS
done
echo "<secret>"

# webserver
echo && echo "Web Server:"
if [ -z "$WEB_SERVER" ]; then
    if which apache2 > /dev/null; then
        WEB_SERVER=apache2
    elif which nginx > /dev/null ; then
        WEB_SERVER=nginx
    fi
    if [ -z "$WEB_SERVER" ]; then
        select WEB_SERVER in apache2 nginx; do
            [ -n "$WEB_SERVER" ] && break
        done
    fi
fi
echo $WEB_SERVER

# flask config
echo && echo "System Configuration:"
if [ -z "$FLASK_CONFIG" ]; then
    select FLASK_CONFIG in product testing; do
        [ -n "$FLASK_CONFIG" ] && break
    done
fi
echo $FLASK_CONFIG

# db
echo && echo "Database:"
while [ -z "$SQLALCHEMY_DATABASE_URI" ]; do
    read -p "Sqlalchemy database URI: " SQLALCHEMY_DATABASE_URI
done
echo $SQLALCHEMY_DATABASE_URI

# celery
echo && echo "Celery Broker:"
while [ -z "$CELERY_BROKER_URL" ]; do
    read -p "Broker URL: " CELERY_BROKER_URL
done
echo $CELERY_BROKER_URL

# ganglia
echo && echo "Ganglia URL:"
while [ -z "$GANGLIA_URL" ]; do
    read -p "Ganglia URL: " GANGLIA_URL
done
echo $GANGLIA_URL


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

stop vinzor-beat || :
stop vinzor-worker || :
stop vinzor-uwsgi || :

clear || :

mkdir -p /var/log/vinzor/install
rm -rf /var/log/vinzor/install/*
logdir=/var/log/vinzor/install

function exec_sh() {
    script=$1
    [ -x "${CURRENT_DIR}/lib/${script}" ] || chmod +x "${CURRENT_DIR}/lib/${script}"
    "${CURRENT_DIR}/lib/${script}" 2>&1 | tee -a "${logdir}/${script}.log" | tee -a "${logdir}/all.log" >> /dev/null
}

# common component #############################################################
echo "------------------ Installing system ------------------"
show_progress "Installing crudini" 20               && exec_sh crudini.sh
show_progress "Installing mysql" 40                 && exec_sh mysql.sh
if [ "$WEB_SERVER" == nginx ]; then
show_progress "Installing nginx" 50                 && exec_sh nginx.sh
else
show_progress "Installing apache2" 50                 && exec_sh apache2.sh
fi
show_progress "Installing rabbitmq" 70              && exec_sh rabbitmq.sh
show_progress "Installing management system" 90     && exec_sh project.sh

# remove env ###################################################################
rm -rf "$TMP_SOURCES_LIST"

show_progress "Done" 100

echo Bye!

