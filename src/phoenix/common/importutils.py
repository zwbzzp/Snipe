# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Import utils
#
# 2016/1/23 lipeizhao: Init


"""
Import related utilities and helper functions.
"""

import sys
import traceback


def import_class(import_str):
    """
    Returns a class from a string including module and class.
    """
    mod_str, _sep, class_str = import_str.rpartition('.')
    __import__(mod_str)
    try:
        return getattr(sys.modules[mod_str], class_str)
    except AttributeError:
        raise ImportError('Class %s cannot be found (%s)' %
                          (class_str,
                           traceback.format_exception(*sys.exc_info())))


def import_object(import_str, *args, **kwargs):
    """
    Import a class and return an instance of it.
    """
    return import_class(import_str)(*args, **kwargs)


def import_object_ns(name_space, import_str, *args, **kwargs):
    """
    Tries to import object from default namespace.
    """
    import_value = "%s.%s" % (name_space, import_str)
    try:
        cls = import_class(import_value)
    except ImportError:
        cls = import_class(import_str)
    return cls(*args, **kwargs)


def import_module(import_str):
    """
    Import a module.
    """
    __import__(import_str)
    return sys.modules[import_str]


def try_import(import_str, default=None):
    """Try to import a module and if it fails return default."""
    try:
        return import_module(import_str)
    except ImportError:
        return default
