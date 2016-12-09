#!/bin/bash
# Install mysql-server

set -e

CONF_NAME=${CONF_NAME:-license_nginx.conf}

CURRENT_DIR=$(cd "$(dirname "$0")"; pwd)
CONF_DIR=$(cd "${CURRENT_DIR}/../conf"; pwd)

# install nginx
apt-get $APT_OPTIONS install -y --force-yes nginx

# nginx configure
rm -f /etc/nginx/nginx.d/license_nginx.conf
cp ${CONF_DIR}/${CONF_NAME} /etc/nginx/conf.d/${CONF_NAME}

service nginx restart
