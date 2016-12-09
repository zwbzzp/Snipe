# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Ping utils
#
# 2016/03/30 fengyingcai: init

import sys
import subprocess


def ping(host, size=32, timeout=1):
    """ Ping a host
    :param host: hostname or address
    :param size: package size
    :param timeout: timeout in seconds
    :return: True if success, otherwise False
    :rtype: bool
    """
    if sys.platform.startswith('win'):
        timeout *= 1000
        PING_CMD = ['ping', '-n', '1', '-l', str(size), '-w', str(timeout)]
    elif sys.platform.startswith('linux'):
        PING_CMD = ['ping', '-c', '1', '-s', str(size), '-W', str(timeout)]
    elif sys.platform.startswith('darwin'):
        PING_CMD = ['ping', '-c', '1', '-s', str(size), '-t', str(timeout)]
    PING_CMD.append(host)
    with subprocess.Popen(PING_CMD) as p:
        return p.wait(timeout=timeout) == 0
