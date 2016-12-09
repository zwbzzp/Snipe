# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 4/21/16 bitson : Init

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import phoenix.config as cfg
from sqlalchemy import create_engine
from phoenix.db.base import BASE


def init():
    engine = create_engine(cfg.CONF.database.connection, echo=True)
    BASE.metadata.create_all(engine)