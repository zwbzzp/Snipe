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

deamon vinzor-license-uwsgi


