# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/7/25 luzh : Init



import telnetlib
from xml.sax.handler import ContentHandler
import xml.sax
# from common.settings.api import vinzor_settings
from decimal import Decimal
import time
import logging
from .. import db, app

LOG = logging.getLogger(__name__)

GANGLIA_URL = app.config['GANGLIA_URL']
ganglia_url = GANGLIA_URL.split('/')[2]
GANGLIA_IP = ganglia_url.split(':')[0]
GANGLIA_PORT = ganglia_url.split(':')[1]

class GangliaHandle(ContentHandler):
    '''
     A handler to parse the ganglia data
    '''
    def __init__(self):
        self.cluster = {'LOCALTIME': 0, 'HOSTNUM': 0, 'UPHOST': 0, 'DOWNHOST': 0, 'CPUNUM': 0,
                        'AVGLOAD_1': 0, 'AVGLOAD_5': 0, 'AVGLOAD_15': 0}
        self.hosts = []
        self.host = {}

    def startElement(self, name, attrs):
        if name == 'CLUSTER':
            self.cluster.update(attrs)
        if name == 'HOST':
            self.host.update(attrs)
        if name == 'METRIC':
            self.host[attrs['NAME']] = attrs['VAL']

    def endElement(self, name):
        if name == 'HOST':
            self.hosts.append(self.host)
            self.host = {}

    def characters(self, chars):
        pass


def host_alive(host, cluster):
    '''
    To determine the host is alive
    '''
    ttl = 60
#     if host['TN'] and host['TMAX']:
#         if host['TN'] > host['TMAX'] * 4:
#             return False
#     else:
#         if abs(cluster['LOCALTIME'] - host['REPORTED']) > 4*ttl:
#             return False
    if abs(int(cluster['LOCALTIME']) - int(host['REPORTED'])) > 4 * ttl:
            return False
    return True


def timestamp_datetime(value):
    '''
    Change the integer format to date string
    '''
    timeformat = '%Y-%m-%d %H:%M:%S'
    value = time.localtime(value)
    dt = time.strftime(timeformat, value)
    return dt


def uptime(timeperiod):
    '''
    Calculate the integer time period to string
    '''
    day = int(timeperiod / 86400)
    timeperiod = timeperiod % (day * 86400) if day != 0 else timeperiod
    hour = int(timeperiod / 3600)
    timeperiod = timeperiod % (hour * 3600) if hour != 0 else timeperiod
    minu = int(timeperiod / 60)
    sec = timeperiod % (minu * 60) if minu != 0 else timeperiod
    days = '' if day == 0 else '%d天' % day
    result = days + '%d小时%d分%d秒' % (hour, minu, sec)
    return result


def telnet_ganglia():
    '''
    Telnet ganglia to achieve cluster data
    '''
    port = 8649
    #port = 8651
    handler = GangliaHandle()

    try:
        tn = telnetlib.Telnet(GANGLIA_IP, port, timeout=5)
        data = tn.read_all()
        xml.sax.parseString(data, handler)
    except ConnectionRefusedError as cerr:
        LOG.exception('%s', cerr)
    except Exception as err:
        LOG.exception('%s', err)
    return handler.cluster, handler.hosts


def hostinitial(onehost):
    '''
    Initial a host info
    '''
    onehost.setdefault('DMAX', None)
    onehost.setdefault('GMOND_STARTED', None)
    onehost.setdefault('IP', None)
    onehost.setdefault('LOCATION', None)
    onehost.setdefault('NAME', None)
    onehost.setdefault('REPORTED', None)
    onehost.setdefault('TMAX', None)
    onehost.setdefault('TN', None)
    onehost.setdefault('boottime', 0)
    onehost.setdefault('bytes_in', 0)
    onehost.setdefault('bytes_out', 0)
    onehost.setdefault('cpu_aidle', 0)
    onehost.setdefault('cpu_idle', 0)
    onehost.setdefault('cpu_nice', 0)
    onehost.setdefault('cpu_num', '0')
    onehost.setdefault('cpu_speed', '0')
    onehost.setdefault('cpu_system', 0)
    onehost.setdefault('cpu_user', 0)
    onehost.setdefault('cpu_wio', 0)
    onehost.setdefault('disk_free', 0)
    onehost.setdefault('disk_total', 1)
    onehost.setdefault('gexec', None)
    onehost.setdefault('load_fifteen', 0)
    onehost.setdefault('load_five', 0)
    onehost.setdefault('load_one', 0)
    onehost.setdefault('machine_type', '')
    onehost.setdefault('mem_buffers', 0)
    onehost.setdefault('mem_cached', 0)
    onehost.setdefault('mem_free', 0)
    onehost.setdefault('mem_shared', 0)
    onehost.setdefault('mem_total', 1)
    onehost.setdefault('os_name', '')
    onehost.setdefault('os_release', '')
    onehost.setdefault('part_max_used', None)
    onehost.setdefault('pkts_in', 0)
    onehost.setdefault('pkts_out', 0)
    onehost.setdefault('proc_run', 0)
    onehost.setdefault('proc_total', 0)
    onehost.setdefault('swap_free', 0)
    onehost.setdefault('swap_total', 0)
    onehost.setdefault('uptime', '0秒')
    onehost.setdefault('cpu_usage', 0)
    onehost.setdefault('mem_usage', 0)
    onehost.setdefault('disk_usage', 0)
    onehost.setdefault('net_out', 0)
    onehost.setdefault('net_in', 0)

    return onehost


def ganglia_info():
    '''
    Calculate the cluster and hosts attributes
    '''
    cluster, hosts = telnet_ganglia()
    cluster['HOSTNUM'] = len(hosts)
    loadone1 = 0
    loadone5 = 0
    loadone15 = 0
    for hostinfo in hosts:
        hostinitial(hostinfo)
        hostinfo['state'] = host_alive(hostinfo, cluster)
        if hostinfo['state']:
            cluster['UPHOST'] += 1
            hostinfo['uptime'] = uptime(int(cluster['LOCALTIME']) - int(hostinfo['boottime']))
            cu = 100 - float(hostinfo['cpu_idle'])
            hostinfo['cpu_usage'] = '{:.2f}'.format(Decimal(cu))
            r = 100 * (1 - float(hostinfo['mem_free']) / float(hostinfo['mem_total']))
            hostinfo['mem_usage'] = '{:.2f}'.format(Decimal(r))
            d = 100 * (1 - float(hostinfo['disk_free']) / float(hostinfo['disk_total']))
            hostinfo['disk_usage'] = '{:.2f}'.format(Decimal(d))
            loadone1 += float(hostinfo['load_one'])
            loadone5 += float(hostinfo['load_five'])
            loadone15 += float(hostinfo['load_fifteen'])
            hostinfo['net_out'] = '{:.2f}'.format(Decimal(float(hostinfo['bytes_out']) / 1024))
            hostinfo['net_in'] = '{:.2f}'.format(Decimal(float(hostinfo['bytes_in']) / 1024))
        else:
            cluster['DOWNHOST'] += 1
            hostinfo['load_one'] = 0
            hostinfo['load_five'] = 0
            hostinfo['load_fifteen'] = 0

        hostinfo['boottime'] = timestamp_datetime(int(hostinfo['boottime']))
        hostinfo['os'] = hostinfo['os_name'] + ' ' + hostinfo['os_release'] + ' (' + hostinfo['machine_type'] + ')'
        cp = float(hostinfo['cpu_speed']) / 1024
        hostinfo['cpu_speed'] = '{:.2f}'.format(Decimal(cp))
        hostinfo['cpus'] = hostinfo['cpu_num'] + ' x ' + hostinfo['cpu_speed'] + 'GHz'
        m = float(hostinfo['mem_total']) / 1024 / 1024
        hostinfo['mem_total'] = '{:.2f}'.format(Decimal(m))
        hostinfo['disk_total'] = round(float(hostinfo['disk_total']), 2)
        hostinfo['proc_run'] = int(hostinfo['proc_run'])
        hostinfo['REPORTED'] = timestamp_datetime(int(hostinfo['REPORTED']))
        cluster['CPUNUM'] += int(hostinfo['cpu_num'])

    cluster['LOCALTIME'] = timestamp_datetime(int(cluster['LOCALTIME']))
    if cluster['UPHOST'] != 0:
        cluster['AVGLOAD_1'] = '{:.2f}'.format(Decimal(loadone1 / cluster['UPHOST']))
        cluster['AVGLOAD_5'] = '{:.2f}'.format(Decimal(loadone5 / cluster['UPHOST']))
        cluster['AVGLOAD_15'] = '{:.2f}'.format(Decimal(loadone15 / cluster['UPHOST']))

    return cluster, hosts
