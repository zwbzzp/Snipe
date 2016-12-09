# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-8-5 qinjinghui : Init
import sys
import os
import ConfigParser


class ZooAgentConfig(object):
    '''
    classdocs
    '''
    zoo_agent_config = "zooagent.conf"

    def __init__(self):
        self.cf = ConfigParser.ConfigParser()
        self.cf.read(self.zoo_agent_config)
        
    def get_ext_hosts(self):
        try:
            return self.cf.get("zookeeper","ext_hosts")
        except:
            return ""

    def get_mgmt_hosts(self):
        try:
            return self.cf.get("zookeeper", "mgmt_hosts")
        except:
            return ""

if __name__ == '__main__':
    zoo_agent_config = ZooAgentConfig()
    print(zoo_agent_config.get_ext_hosts())
    print(zoo_agent_config.get_mgmt_hosts())