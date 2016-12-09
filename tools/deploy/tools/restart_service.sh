#!/bin/bash
# restart project service

set -e

function deamon() {
    process=$1
    if (status ${process} | grep stop > /dev/null) ; then
        start ${process}
    else
        restart ${process}
    fi
    echo process ${process} started
}

deamon vinzor-sync_openstack
deamon vinzor-beat
deamon vinzor-worker
deamon vinzor-uwsgi


