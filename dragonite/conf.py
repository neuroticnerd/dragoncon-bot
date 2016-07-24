# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import io
import logging
import sys

from collections import OrderedDict
from dateutil.parser import parse

from armory.environ import Environment
from armory.serialize import jsonify, jsonexpand

from .comm import CommProxy

if (sys.version_info > (3, 0)):
    # FileNotFoundError is built-in in Python 3
    pass
else:
    FileNotFoundError = (IOError, OSError)


class DragoniteCache(object):
    def __init__(self, tofile=False, cachefile=None):
        self._data = {}
        self._tofile = tofile
        self.cachefile = cachefile or '.dragonite'
        try:
            with io.open(self.cachefile, 'r', encoding='utf-8') as cf:
                raw = cf.read()
                if raw:
                    self._data.update(jsonexpand(raw))
            if 'event_start' in self._data:
                self._data['event_start'] = parse(self._data['event_start'])
            if 'event_end' in self._data:
                self._data['event_end'] = parse(self._data['event_end'])
        except FileNotFoundError:
            pass

    def __getitem__(self, item):
        return self._data[item]

    def __setitem__(self, item, value):
        self._data[item] = value

    def get(self, item, default=None):
        return self._data.get(item, default)

    def flush(self):
        if not self._tofile:
            return
        with io.open(self.cachefile, 'w', encoding='utf-8') as cf:
            cf.write(jsonify(self._data, True))


class DragoniteConfig(object):
    levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARNING,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL,
    }
    fmt_long = '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s'
    fmt_short = '%(message)s'
    fmt_date = '%Y-%m-%d %H:%M:%S'

    def __init__(self, **options):
        self._warnings = []
        self._logconf = {}
        self.env = Environment({
            'DRAGONITE_LOGLEVEL': {'default': 'info'},
        })

        ll = options.get('loglevel', None)
        if ll is None:
            try:
                ll = self.env('DRAGONITE_LOGLEVEL')
                self.loglevel = self.levels[ll.lower()]
            except KeyError:
                errmsg = 'ignoring env var {0} with invalid value of {1}'
                self._warnings.append(errmsg.format('DRAGONITE_LOGLEVEL', ll))
                self.loglevel = logging.INFO
        else:
            try:
                self.loglevel = self.levels[ll.lower()]
            except KeyError:
                errmsg = 'ignoring option loglevel with invalid value of {0}'
                self._warnings.append(errmsg.format(ll))
                self.loglevel = logging.INFO

        self.verbose = bool(options.get('verbose', False))

        cc = options.get('cache', None)
        if cc is None:
            self.use_cache = False
        else:
            self.use_cache = bool(cc)

        self.interval = 1
        self.max_attempts = options.get('max_attempts', 0)
        self.debug = options.get('debug', False)
        self.info = options.get('info', True)
        self.simple = options.get('simple', False)

        self.comm = CommProxy(settings=self)

    @property
    def cache(self):
        if not hasattr(self, '_cache'):
            self._cache = DragoniteCache(tofile=self.use_cache)
        return self._cache

    def __str__(self):
        return '{0}'.format({
            'loglevel': self.loglevelname,
            'use_cache': self.use_cache,
        })

    def get_logger(self, logname, loglevel=None):
        """https://gist.github.com/neuroticnerd/7c60d61c8d9d9716f50d"""
        conf_once = self._logconf.get(logname, True)
        logger = logging.getLogger(logname)
        if conf_once:
            logger.propagate = False
            ll = self.loglevel if loglevel is None else loglevel
            logger.setLevel(ll)
            msgfmt = self.fmt_long if self.verbose else self.fmt_short
            formatter = logging.Formatter(fmt=msgfmt, datefmt=self.fmt_date)
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            self._logconf[logname] = False
        return logger

    @property
    def loglevel(self):
        if not hasattr(self, '_loglevel'):
            self._loglevel = self.levels['info']
        return self._loglevel

    @loglevel.setter
    def loglevel(self, value):
        if value not in self.levels.values():
            try:
                self._loglevel = self.levels[value]
            except KeyError:
                errmsg = '{0} is not a valid logging level!'
                raise ValueError(errmsg.format(value))
        else:
            self._loglevel = value

    @property
    def loglevelname(self):
        return logging.getLevelName(self.loglevel)

    @property
    def sms_enabled(self):
        return self.cache.get('send_sms', False)

    @property
    def email_enabled(self):
        return self.cache.get('send_email', False)

    def dumps(self, pretty=False):
        config = OrderedDict()
        config['debug'] = self.debug
        config['info'] = self.info
        config['simple'] = self.simple
        config['use_cache'] = self.use_cache
        config['max_attempts'] = self.max_attempts
        config['loglevel'] = self.loglevel
        config['loglevelname'] = self.loglevelname
        config['verbose'] = self.verbose
        config['interval'] = self.interval
        config['sms_enabled'] = self.sms_enabled
        config['email_enabled'] = self.email_enabled
        return jsonify(config, pretty=pretty)


settings = DragoniteConfig()
