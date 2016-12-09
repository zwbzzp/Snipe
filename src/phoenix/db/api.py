# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Database API
#
# 20160113 fengyingcai : Create the database api for CRUD operations
import os
import logging
import functools
import contextlib

from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session, Session
from sqlalchemy import and_, or_

import phoenix.config as cfg
from phoenix.db import ModelBase, FloatingIp
from phoenix.db import exception as db_exc

basedir = os.path.abspath((os.path.dirname(__file__)))

db_options = [
    cfg.StrOpt('connection', default='mysql+pymysql://root:admin123@127.0.0.1:3306/phoenix',
               help='The sqlalchemy connection string'),
    cfg.IntOpt('pool_recycle', default=3600,
               help='Seconds before idle sql connections are reaped'),
    cfg.IntOpt('pool_timeout', default=30,
               help='Seconds before giving up on getting a connection from the pool'),
    cfg.IntOpt('min_poolsize', default=1,
               help='Minimum number of connections to keep opened in a session'),
    cfg.IntOpt('pool_size', default=100,
               help='Maximum number of connections to keep opened in a session'),
    cfg.IntOpt('max_overflow', default=10,
               help='If set, use this value for max_overflow with sqlalchemy'),
]

cfg.CONF.register_opts(db_options, group='database')

LOG = logging.getLogger(__name__)

# Shared engine
_ENGINE = None


def get_engine():
    """ Get a share database engine
    :return: Database engine
    :rtype: sqlalchemy.engine.Engine
    """
    global _ENGINE

    if not _ENGINE:
        # cfg.CONF(default_config_files=[CONF_DIR], args=None)

        sql_connection = cfg.CONF.database.connection
        engine_kargs = {
            'convert_unicode': True,
        }
        if cfg.CONF.database.pool_recycle is not None:
            engine_kargs['pool_recycle'] = cfg.CONF.database.pool_recycle
        # if cfg.CONF.database.pool_timeout is not None:
        #     engine_kargs['pool_timeout'] = cfg.CONF.database.pool_timeout
        # if cfg.CONF.database.min_poolsize is not None:
        #     engine_kargs['min_poolsize'] = cfg.CONF.database.min_poolsize
        if cfg.CONF.database.pool_size is not None:
             engine_kargs['pool_size'] = cfg.CONF.database.pool_size
        if cfg.CONF.database.max_overflow is not None:
            engine_kargs['max_overflow'] = cfg.CONF.database.max_overflow
        _ENGINE = create_engine(sql_connection, **engine_kargs)
    return _ENGINE


def get_session():
    """ Get a database session
    :return: Database session
    :rtype: sqlalchemy.orm.session.Session
    """
    engine = get_engine()
    #return scoped_session(sessionmaker(bind=engine))
    Session = sessionmaker(bind=engine)
    return Session()


@contextlib.contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = get_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def transactional(fn):
    """ Transactional decorator
    :param fn: a function with session param
    :return:
    """
    @functools.wraps(fn)
    def transact(*args, **kwargs):
        session = get_session()
        with session.begin():
            fn(*args, session=session, **kwargs)
    return transact


@contextlib.contextmanager
def begin_transaction(session=None, nested=False):
    """ Transaction context manager
    :param session: sqlalchemy.orm.session.Session
    :param nested:
    :return:
    """
    if session is None:
        session = get_session()
    tran = session.begin(nested=nested)
    try:
        yield tran
        tran.commit()
    except:
        raise
    finally:
        tran.rollback()


def autorollback(fn):
    """ Auto rollback decorator
    :param fn:
    :return:
    """
    def rollback(*args, **kwargs):
        session = get_session()
        tran = session.begin()
        try:
            fn(*args, session=session, **kwargs)
        finally:
            tran.rollback()
    rollback.__name__ = fn.__name__
    return rollback


def model_query(context, model, session=None, args=None):
    """Query helper for db api methods.

    :param model:        Model to query. Must be a subclass of ModelBase.
    :type model:         models.ModelBase

    :param session:      The session to use.
    :type session:       sqlalchemy.orm.session.Session

    :param args:         Arguments to query. If None - model is used.
    :type args:          tuple

    """

    if hasattr(context, 'session'):
        session = context.session

    if session is None:
        session = get_session()

    if not issubclass(model, ModelBase):
        raise TypeError("model should be a subclass of ModelBase")
    with session.begin(subtransactions=True):
        query = session.query(model) if not args else session.query(*args)

    return query


##################
# scheduler

##################
# floating ip

def get_all_floating_ips():
    """Get all floating ips"""
    with session_scope() as session:
        instances = session.query(FloatingIp).all()
        session.expunge_all()
        return instances
        #return model_query(None, FloatingIp).all()


def get_floating_ips(sort_col=None, search=None):
    """Get the search floadting ips which can be sorted"""
    with session_scope() as session:
        query = session.query(FloatingIp).order_by(sort_col)
        if search:
            query = query.filter(or_(FloatingIp.ip_address.like("%" + search
                                                                + "%"), None))
        session.expunge_all()
        return query


def get_last_sync_time():
    """Get the floadting ips' last sync time"""
    with session_scope() as session:
        # FIXME: here we use the created time as the last sync time,
        last_update_one = session.query(FloatingIp).order_by("created_at desc").first()
        session.expunge_all()
        return last_update_one.created_at if last_update_one else None


def get_floating_ip_by_ref_id(fip_ref_id):
    """Fetch the floating ip through ref_id"""
    with session_scope() as session:
        fip = session.query(FloatingIp).filter_by(ref_id=fip_ref_id).first()
        session.expunge_all()
        return fip


def create_floating_ip(ip):
    """Create floating ip"""
    session = get_session()
    try:
        session.add(ip)
        session.commit()
        LOG.info("Floating ip %s created" % ip.ip_address)
    except db_exc.DBDuplicateEntry as e:
        pass
    return ip


def delete_floating_ip(id):
    """Delete floating ip"""
    session = get_session()
    ip = session.query(FloatingIp).filter(FloatingIp.id == id).first()

    if ip:
        session.delete(ip)
        session.commit()


def delete_all_floating_ip():
    """Delete all floating ip"""
    session = get_session()
    count = session.query(FloatingIp).delete()
    session.commit()


def allocate_floating_ip(external_network_id):
    """Allocate local floating ip"""
    session = get_session()
    ip = session.query(FloatingIp).with_for_update().\
        filter(FloatingIp.external_network_id == external_network_id,
               FloatingIp.status == FloatingIp.IP_STATUS.DOWN).first()
    if ip:
        ip.status = FloatingIp.IP_STATUS.ACTIVE
        session.add(ip)
    session.commit()
    return ip


def allocate_floating_ip_by_ref_id(fip_ref_id):
    """Allocate local floating ip through ref id"""
    session = get_session()
    ip = session.query(FloatingIp).with_for_update().\
        filter(FloatingIp.ref_id == fip_ref_id,
               FloatingIp.status == FloatingIp.IP_STATUS.DOWN).first()
    if ip:
        ip.status = FloatingIp.IP_STATUS.ACTIVE
        session.add(ip)
    session.commit()
    return ip


def reclaim_floating_ip(ip_address):
    """Reclaim local floating ip"""
    session = get_session()
    ip = session.query(FloatingIp).with_for_update().\
        filter(FloatingIp.ip_address == ip_address).first()
    ip.status = FloatingIp.IP_STATUS.DOWN
    session.add(ip)
    session.commit()


def delete_floating_ip_by_ref_id(fip_ref_id):
    """Delete local floating ip through ref id"""
    session = get_session()
    ip = session.query(FloatingIp).with_for_update().\
        filter(FloatingIp.ref_id == fip_ref_id).first()

    if ip:
        session.delete(ip)
    session.commit()