# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Singleton mixin
#
# 20160113 lipeizhao : Create the Singleton mixin

import threading
import abc


class SingletonMixin(object):
    """A thread safe Singleton mixin.

    e.g.::

        # put SingletonMixin as one of the base class
        class MyClass(SingletonMixin, OtherClass):
            ...
    """

    __instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # if SingletonMixin.__instance is None:
        #     with SingletonMixin._lock:
        #         if SingletonMixin.__instance is None:
        #             SingletonMixin.__instance = super(SingletonMixin, cls).__new__(cls, *args, **kwargs)
        # return cls.__instance
        if cls.__instance is None:
            with cls._lock:
                if cls.__instance is None:
                    cls.__instance = super(SingletonMixin, cls).__new__(cls, *args, **kwargs)
        return cls.__instance


class LocalSingletonMixin(object):
    """ A thread local singleton mixin.
    """

    # A thread local storage
    __thread_local = threading.local()

    def __new__(cls, *args, **kwargs):
        instance = getattr(cls.__thread_local, str(cls), None)
        if instance is None:
            # Always safe to init a thread local instance as it is serial
            # Does not need a thread lock
            instance = super(LocalSingletonMixin, cls).__new__(cls, *args, **kwargs)
            setattr(cls.__thread_local, str(cls), instance)
        return instance


class LocalSingletonExpireMixin(object):
    """ A thread local singleton with auto expire mixin
    """
    __metaclass__ = abc.ABCMeta

    __thread_local = threading.local()

    def __new__(cls, *args, **kwargs):
        instance = getattr(cls.__thread_local, str(cls), None)
        if instance is None or instance.is_expired():
            # Delete current instance
            del instance
            # Always safe to init a thread local instance as it is serial
            # Does not need a thread lock
            instance = super(LocalSingletonExpireMixin, cls).__new__(cls, *args, **kwargs)
            setattr(cls.__thread_local, str(cls), instance)
        return instance

    @abc.abstractmethod
    def __delete__(self, instance):
        raise NotImplementedError

    @abc.abstractmethod
    def is_expired(self):
        raise NotImplementedError