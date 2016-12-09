# -*- coding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Config
#
# 2016/04/13 fengyc : Init

import os
import functools
import configparser
import logging
from .exception import BaseException

LOG = logging.getLogger()


class OptException(BaseException):
    """Opt Exception"""
    pass


class Opt(object):
    """Generic option class"""

    def __init__(self, key, default=None, **kwargs):
        self.key = key
        self.default = default
        self._value = None
        self.__dict__.update(**kwargs)

    def parse(self, opt_value):
        """ Parse an option value (a string) to a value (int, list, map ...)
        :param opt_value:
        :return:
        """
        return opt_value

    def _get_value(self):
        return self._value if self._value is not None else self.default

    def _set_value(self, v):
        self._value = self.parse(v)

    value = property(_get_value, _set_value)


class StrOpt(Opt):
    """String option"""
    pass


class IntOpt(Opt):
    """Integer option"""

    def __init__(self, *args, **kwargs):
        if kwargs.get('default') is not None:
            kwargs['default'] = self.parse(kwargs['default'])
        super(IntOpt, self).__init__(*args, **kwargs)

    def parse(self, v):
        try:
            value = int(v)
        except Exception as ex:
            raise OptException('IntOpt %s should be an integer' % self.key)
        return value


class FloatOpt(Opt):
    """Float option"""

    def __init__(self, *args, **kwargs):
        if kwargs.get('default') is not None:
            kwargs['default'] = self.parse(kwargs['default'])
        super(FloatOpt, self).__init__(*args, **kwargs)

    def parse(self, v):
        try:
            value = float(v)
        except Exception as ex:
            raise OptException('FloatOpt %s should be a float' % self.key)
        return value


class OptGroup(object):
    def __init__(self, key, opts=[], items={}):
        self.key = key
        self._opts = dict(((opt.key, opt) for opt in opts))
        self._items = items

    def __getattr__(self, item):
        opt = self._opts[item]
        if opt.value is None:
            return opt.default
        return opt.value

    def register_opt(self, opt):
        if self._opts.get(opt.key):
            old_opt = self._opts[opt.key]
            if (old_opt.__class__ != opt.__class__) or \
                    (old_opt.default != opt.default):
                raise OptException('Duplicated option %s in group %s' %
                                   (opt.key, self.key))
        self._opts[opt.key] = opt
        if self._items.get(opt.key):
            opt.value = self._items[opt.key]

    def import_opt(self, opt_name):
        if self._opts.get(opt_name) is None:
            raise OptException('Option %s not registered yet' % (opt_name))

    def update_items(self, items):
        self._items = items
        for opt in self._opts.values():
            if self._items.get(opt.key):
                opt.value = self._items[opt.key]


class FormatHandler(object):
    def __init__(self):
        pass

    def load_content(self, content):
        """Load and verify the content"""
        pass

    def load_file(self, filename):
        """Load and verify the file"""
        pass

    @property
    def group_items(self):
        """Group items from file"""
        pass


class INIFormatHandler(FormatHandler):
    def __init__(self):
        self.parser = configparser.ConfigParser()
        self._dict = dict()

    def __load(self):
        for (s, o) in self.parser.items():
            if self._dict.get(s) is None:
                self._dict[s] = dict()
            for (k, v) in o.items():
                self._dict[s][k] = v
        LOG.debug(self._dict)

    def load_file(self, filename):
        self.parser.read(filename)
        self.__load()

    def load_content(self, content):
        self.parser.read_string(content)
        self.__load()

    @functools.lru_cache()
    def group_items(self):
        return self._dict.items()


SUFFIX_FORMAT = {
    'ini': INIFormatHandler,
}


def find_config_files(extensions=['.ini']):
    """Find default config files"""

    config_dirs = [
        '/etc/vinzor',
        os.path.join(os.path.dirname(__file__), '../etc')
    ]
    # get file list
    files = []
    for d in config_dirs:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if os.path.isfile(f) and os.access(f, os.R_OK):
                    files.append(f)
    # check file extension
    config_files = []
    for f in files:
        for e in extensions:
            if f.endswith(e):
                config_files.append(f)
                break
    return config_files


class Config(object):
    """Config container"""

    def __init__(self):
        self._groups = dict()
        self._items = dict()

    def __getattr__(self, item):
        g = self._groups[item]
        return g

    def __call__(self, default_config_files=None, *args, **kwargs):
        if not default_config_files:
            default_config_files = find_config_files()
        for f in default_config_files:
            self.from_file(f)

    def clear(self):
        self._groups = dict()
        self._items = dict()

    def _update_item(self, k, sub_items):
        if self._items.get(k) is None:
            self._items[k] = {}
        for (s, v) in sub_items.items():
            self._items[k][s] = v
        # update group items
        if self._groups.get(k):
            self._groups[k].update_items(self._items[k])

    def from_file(self, filename, format=None):
        format = format or filename[filename.rindex('.') + 1:]
        handler_cls = SUFFIX_FORMAT[format]
        handler = handler_cls()
        handler.load_file(filename)
        for (k, v) in handler.group_items():
            self._update_item(k, v)

    def from_string(self, content, format):
        handler_cls = SUFFIX_FORMAT[format]
        handler = handler_cls()
        handler.load_content(content)
        for (k, v) in handler.group_items():
            self._update_item(k, v)

    def register_opts(self, opts, group='DEFAULT'):
        g = self._groups.get(group)
        if g is None:
            g = OptGroup(group, [], self._items.get(group) or {})
        for opt in opts:
            g.register_opt(opt)
        self._groups[group] = g

    def import_opt(self, opt_name, group='DEFAULT'):
        g = self._groups[group]
        g.import_opt(opt_name)


# Default config object
CONF = Config()
