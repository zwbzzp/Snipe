#!/bin/bash
# Install rqbbitmq and configure it.

set -e
set -o pipefail

# Installation could be failed if network configuration is wrong.

RABBIT_USER=${RABBIT_USER:-guest}
RABBIT_PASS=${RABBIT_PASS:-guest}

# Install rabbitmq
apt-get $APT_OPTIONS install -y --force-yes rabbitmq-server

# Update rabbitmq user password
( rabbitmqctl list_users | grep ${RABBIT_USER} ) || rabbitmqctl add_user $RABBIT_USER $RABBIT_PASS
rabbitmqctl change_password $RABBIT_USER $RABBIT_PASS
rabbitmqctl set_permissions -p '/' $RABBIT_USER ".*" ".*" ".*"

service rabbitmq-server restart
