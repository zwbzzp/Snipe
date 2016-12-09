#!/bin/bash

set -e
set -o pipefail

if [ $(id -u) -ne 0 ]; then
    echo "Please run with root user" && exit 1
fi

# check system
if ! which python2 > /dev/null ; then
    echo "Can not find python2" && exit 1
fi
if ! which nova-compute > /dev/null ; then
    echo "Can not find nova-compute" && exit 1
fi
if ! which pip > /dev/null ; then
    echo "Can not find pip" && exit 1
fi

CUR_DIR="$(cd "$(dirname "$0")"; pwd)"

while [ -z "$DEST_DIR" ]; do
    read -p 'Installation directory (default: /usr/share/zooagent):' DEST_DIR
    [ -z "$DEST_DIR" ] && DEST_DIR=/usr/share/zooagent
done
while [ -z "$EXT_HOSTS" ]; do
    read -p 'ZooKeeper server public ip:' EXT_HOSTS
    #[ -z "$EXT_HOSTS" ] && NOVA_CONF=/etc/nova/nova.conf
done
while [ -z "$MGMT_HOSTS" ]; do
    read -p 'ZooKeeper server management ip:' MGMT_HOSTS
    #[ -z "$NOVA_COMPUTE_CONF" ] && NOVA_COMPUTE_CONF=/etc/nova/nova-compute.conf
done
echo "Confirmed?"
select CONFIRM in Yes No; do
    [ -n "$CONFIRM" ] && break
done
[ "$CONFIRM" == "No" ] && exit 0

mkdir -p "$DEST_DIR"

# copy to DEST_DIR
echo && echo "Copying to installation directory"
rm -rf "$DEST_DIR/*"
cp -aL $CUR_DIR/zooagent/* "$DEST_DIR"
cp -f "$CUR_DIR/etc/vinzor/zooagent.conf" "$DEST_DIR"
# install service
cp -f "$CUR_DIR/etc/init.d/zooagent" /etc/init.d
sed -e "s|^[[:space:]]*WORK_DIR.*|WORK_DIR=$DEST_DIR|g" \
    -i /etc/init.d/zooagent
sed -e "s|^[[:space:]]*ext_hosts.*|ext_hosts=$EXT_HOSTS|g" \
    -i $DEST_DIR/zooagent.conf
sed -e "s|^[[:space:]]*mgmt_hosts.*|mgmt_hosts=$MGMT_HOSTS|g" \
    -i $DEST_DIR/zooagent.conf
# setting uninstall.sh
sed -e "s|^[[:space:]]*INSTALL_DIR.*|INSTALL_DIR=$DEST_DIR|g" \
    -i "$CUR_DIR/uninstall.sh"

chmod +x /etc/init.d/zooagent
update-rc.d -f zooagent defaults

echo && echo "Installing requirements"
pip install -r "$CUR_DIR/requirements.txt"

service zooagent start

echo "Install finish, you can confirm it in $DEST_DIR"