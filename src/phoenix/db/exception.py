# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd
#
# database exceptions
#
# 20160119 lipeizhao: Init


class DBError(Exception):

    """Base exception for all custom database exceptions.

    :kwarg inner_exception: an original exception which was wrapped with
        DBError or its subclasses.
    """

    def __init__(self, inner_exception=None):
        self.inner_exception = inner_exception
        super(DBError, self).__init__(str(inner_exception))


class DBDuplicateEntry(DBError):
    """Duplicate entry at unique column error.

    Raised when made an attempt to write to a unique column the same entry as
    existing one. :attr: `columns` available on an instance of the exception
    and could be used at error handling::

       try:
           instance_type_ref.save()
       except DBDuplicateEntry as e:
           if 'colname' in e.columns:
               # Handle error.

    :kwarg columns: a list of unique columns have been attempted to write a
        duplicate entry.
    :type columns: list
    :kwarg value: a value which has been attempted to write. The value will
        be None, if we can't extract it for a particular database backend. Only
        MySQL and PostgreSQL 9.x are supported right now.
    """
    def __init__(self, columns=None, inner_exception=None, value=None):
        self.columns = columns or []
        self.value = value
        super(DBDuplicateEntry, self).__init__(inner_exception)