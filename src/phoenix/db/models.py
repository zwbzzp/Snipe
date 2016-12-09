# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd
#
# Data models
#
# 20160114 fengyingcai: Init

from sqlalchemy import Column, UniqueConstraint, Index
from sqlalchemy import String, Boolean, Integer, ForeignKey
from sqlalchemy import Table


from phoenix.db.base import BASE, ModelBase


class FloatingIp(BASE, ModelBase):
    class IP_STATUS():
        ACTIVE = 'active'
        DOWN = 'down'

    __tablename__ = 'floating_ips'
    ref_id = Column(String(64))
    ip_address = Column(String(64))
    external_network_id = Column(String(64))
    status = Column(String(64))

    def __repr__(self):
        return '<Floating ip %r>' % self.ip_address







