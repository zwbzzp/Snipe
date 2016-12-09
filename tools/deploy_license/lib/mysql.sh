#!/bin/bash

set -e

MYSQL_USER=${MYSQL_USER:-root}
MYSQL_PASS=${MYSQL_PASS:-admin123}
MYSQL_INSTALL=${MYSQL_INSTALL:-yes}

# Install mysql-server
if ( echo ${MYSQL_INSTALL} | grep -iE 'yes|true' ); then
    cat << EOF | debconf-set-selections
mysql-server mysql-server/root_password password $MYSQL_PASS
mysql-server mysql-server/root_password_again password $MYSQL_PASS
mysql-server mysql-server/start_on_boot boolean true
EOF
    apt-get $APT_OPTIONS install -y --force-yes mysql-server
fi

# mysql parameters
if ! grep -E '^[[:space:]]*!includedir[[:space:]]*/etc/mysql/conf.d(/)?[[:space:]]*' /etc/mysql/my.cnf; then
    echo '!includedir /etc/mysql/conf.d/' >> /etc/mysql/my.cnf
fi

mkdir -p /etc/mysql/conf.d/
touch /etc/mysql/conf.d/vinzor-license.cnf
cfg="/etc/mysql/conf.d/vinzor-license.cnf"

crudini --set $cfg mysqld skip-name-resolve
crudini --set $cfg mysqld bind-address 0.0.0.0
crudini --set $cfg mysqld default-storage-engine innodb
crudini --set $cfg mysqld innodb_file_per_table
crudini --set $cfg mysqld collation-server utf8_general_ci
crudini --set $cfg mysqld init-connect "'SET NAMES utf8'"
crudini --set $cfg mysqld character-set-server utf8

service mysql restart
