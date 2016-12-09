#!/bin/bash

set -e
set -o pipefail

INSTALL_DIR=/usr/share/zooagent
PY_MODULE="ZooAgent.py"

if [ $(id -u) -ne 0 ]; then
    echo "Please run with root user" && exit 1
fi

check_running()
{
    ps -ef | grep "$PY_MODULE" | grep -v 'grep' > /dev/null
}

do_stop()
{
    if check_running ; then
        ps -ef | grep "$PY_MODULE" | grep -v 'grep' | awk '{print $2}' | xargs kill
    fi
}

do_stop
rm -rf $INSTALL_DIR
update-rc.d -f zooagent remove
rm -f /etc/init.d/zooagent

echo "Uninstall finish"