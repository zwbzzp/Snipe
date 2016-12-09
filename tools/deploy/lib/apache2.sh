#!/bin/bash

set -e

CONF_NAME=${CONF_NAME:-phoenix.conf}

CURRENT_DIR=$(cd "$(dirname "$0")"; pwd)
CONF_DIR=$(cd "${CURRENT_DIR}/../conf/apache2"; pwd)

apt-get $APT_OPTIONS install -y --force-yes apache2 apache2-utils \
    libapache2-mod-proxy-uwsgi

a2enmod proxy
a2enmod proxy_uwsgi

# copy configuration to apache2
if [ -d "/etc/apache2/conf-available" ]; then
    cp -f ${CONF_DIR}/${CONF_NAME} /etc/apache2/conf-available/${CONF_NAME}
fi
if [ -d /etc/apache2/conf.d ]; then
    cp -f ${CONF_DIR}/${CONF_NAME} /etc/apache2/conf.d/${CONF_NAME}
fi

# enable configuration
a2enconf phoenix
service apache2 restart
