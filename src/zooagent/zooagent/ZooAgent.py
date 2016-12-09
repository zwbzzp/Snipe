# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-8-5 qinjinghui : Init

import os, sys
import logging
import logging.handlers
import time
import socket
from multiprocessing import Process
from kazoo.client import KazooClient, KazooState
from kazoo.exceptions import NoNodeError
from config import ZooAgentConfig


LOG_FILE = "."+ os.sep + "log"  + os.sep + "zoo.log"
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes = 20*1024*1024, backupCount = 10);
fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)s]"
formatter = logging.Formatter(fmt);
handler.setFormatter(formatter);  
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

class ZooAgent():

    def __init__(self):
        zoo_agent_config = ZooAgentConfig()
        self.ext_hosts = zoo_agent_config.get_ext_hosts()
        self.mgmt_hosts = zoo_agent_config.get_mgmt_hosts()
        print('->', self.ext_hosts, self.mgmt_hosts)


    def connect_zoo_server_from_ext_net(self):
        if self.ext_hosts == "":
            logger.error("No valid ext hosts.")
            exit(-1)
        try:
            zkc = KazooClient(hosts=self.ext_hosts)
            session_id = []
            hostname = self.__get_hostname()
            if hostname == "":
                logger.error("No Valid Hostname.")
                exit(-1)

            @zkc.add_listener
            def my_listener(state):
                print("my state: ", state)
                if state == KazooState.CONNECTED:
                    try:
                        if session_id and session_id[0] == zkc._session_id:
                            print('reconnected, session isnot expired')
                        else:
                            if session_id:
                                session_id[0] = zkc._session_id
                            else:
                                session_id.append(zkc._session_id)
                            def handler():
                                try:
                                    zkc.delete('/monitor/ext/' + hostname, recursive=True)
                                except NoNodeError:
                                    pass
                                except Exception as ex:
                                    pass
                                finally:
                                    zkc.create('/monitor/ext/' + hostname, b'123', ephemeral=True, makepath=True)
                                    print('create znode')
                            zkc.handler.spawn(handler)
                    except Exception as ex:
                        logger.exception(ex)
            zkc.start()

            while True:
                time.sleep(3600)
        except:
            logging.exception("connect_zoo_server_from_ext_net occurs exception.")


    def connect_zoo_server_from_mgmt_net(self):
        if self.mgmt_hosts == "":
            logger.error("No valid mgmt hosts.")
            exit(-1)
        try:
            zkc = KazooClient(hosts=self.mgmt_hosts)
            session_id = []
            hostname = self.__get_hostname()
            if hostname == "":
                logger.error("No Valid Hostname.")
                exit(-1)
            @zkc.add_listener
            def my_listener(state):
                print("my state: ", state)
                if state == KazooState.CONNECTED:
                    try:
                        if session_id and session_id[0] == zkc._session_id:
                            print('reconnected, session isnot expired')
                        else:
                            if session_id:
                                session_id[0] = zkc._session_id
                            else:
                                session_id.append(zkc._session_id)
                            def handler():
                                try:
                                    zkc.delete('/monitor/mgmt/' + hostname, recursive=True)
                                except NoNodeError:
                                    pass
                                except Exception as ex:
                                    pass
                                finally:
                                    zkc.create('/monitor/mgmt/' + hostname, b'123', ephemeral=True, makepath=True)
                                    print('create znode')
                            zkc.handler.spawn(handler)
                    except Exception as ex:
                        logger.exception(ex)
            zkc.start()
            while 1:
                time.sleep(3600)
        except:
            logging.exception("connect_zoo_server_from_mgmt_net occurs exception.")

    def __get_hostname(self):
        try:
            return socket.gethostname()
        except:
            return ""

def main(argv):
    zooagent = ZooAgent()
    connect_ext_process = Process(target=zooagent.connect_zoo_server_from_ext_net)
    connect_ext_process.start()
    connect_mgmt_process = Process(target=zooagent.connect_zoo_server_from_mgmt_net)
    #connect_ext_process.join()
    connect_mgmt_process.start()

if __name__ == '__main__':
    main(sys.argv)




