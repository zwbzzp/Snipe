# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# 20160112 fengyingcai : db base

from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import object_mapper
from phoenix.common import timeutils

BASE = declarative_base()


class TimestampMixin(object):
    """ Timestamp mixin
    """
    created_at = Column(DateTime, default=lambda: timeutils.utcnow())
    updated_at = Column(DateTime, onupdate=lambda: timeutils.utcnow())


class SoftDeletedMixin(object):
    """ Soft delete mixin
    """
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)

    def soft_delete(self, session):
        self.deleted = True
        self.deleted_at = timeutils.utcnow()
        self.save(session=session)


class ModelBase(TimestampMixin, SoftDeletedMixin):
    """Base class for models"""
    id = Column(Integer, autoincrement=True, primary_key=True, nullable=False)

    def save(self, session):
        """Save this object
        :param session: sqlalchemy session
        :type session: sqlalchemy.orm.session.Session
        """
        with session.begin(subtransactions=True):
            session.add(self)
            session.flush()

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    @property
    def _extra_keys(self):
        """Specifies custom fields

        Subclasses can override this property to return a list
        of custom fields that should be included in their dict
        representation.
        """
        return []

    def __iter__(self):
        """ Make model objects iterable
        """
        columns = dict(object_mapper(self).columns).keys()
        columns.extend(self._extra_keys)
        return columns

    def items(self):
        """Make model objects like a dict
        :return: (k,v) items of model
        :rtype: tuple
        """
        return ((k, getattr(self, k)) for k in self)

    def iteritems(self):
        return self.items()

    def update(self, values):
        """Make model objects like a dict

        :param values: dict
        :type values: dict
        """
        for k in values:
            setattr(self, k, values[k])

