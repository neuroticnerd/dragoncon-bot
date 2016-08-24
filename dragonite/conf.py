# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import io
import logging
import logging.config
import sys
from collections import OrderedDict

from armory.environ import Environment
from armory.serialize import jsonexpand, jsonify

from dateutil.parser import parse

from .comm import CommProxy

if (sys.version_info > (3, 0)):
    # FileNotFoundError is a built-in for Python 3
    pass
else:
    FileNotFoundError = (IOError, OSError)

LOGGING_VERBOSITY_DEFAULT = 'levelname'
LOGGING_LEVEL_DEFAULT = 'INFO'
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(message)s',
        },
        'levelname': {
            'format': '[%(levelname)s] %(message)s',
        },
        'normal': {
            'format': '[%(levelname)s] %(name)s:%(lineno)d  %(message)s',
        },
        'verbose': {
            'format': (
                '[%(levelname)s] %(name)s:%(funcName)s:%(lineno)d  %(message)s'
            ),
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': LOGGING_VERBOSITY_DEFAULT,
        },
    },
    'loggers': {
        '': {
            'level': LOGGING_LEVEL_DEFAULT,
            'handlers': ['console'],
            'propagate': False,
        },
        'dragonite': {
            'level': LOGGING_LEVEL_DEFAULT,
            'handlers': ['console'],
            'propagate': False,
        },
        'requests': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        }
    },
}


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
    fmt_long = '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s'
    fmt_short = '%(message)s'
    fmt_date = '%Y-%m-%d %H:%M:%S'
    MAX_PRICE = 300

    def __init__(self, **options):
        if options:
            self.setup(**options)

    def configure(self, **options):
        self._warnings = []
        self._logconf = {}
        self.env = Environment({
            'DRAGONITE_LOGLEVEL': {'default': 'info'},
        })

        ll = options.get('loglevel', None)
        if ll is None:
            try:
                self.loglevel = self.env('DRAGONITE_LOGLEVEL').upper()
            except KeyError:
                errmsg = 'ignoring env var {0} with invalid value of {1}'
                self._warnings.append(errmsg.format('DRAGONITE_LOGLEVEL', ll))
                self.loglevel = 'INFO'
        else:
            try:
                self.loglevel = ll.upper()
            except KeyError:
                errmsg = 'ignoring option loglevel with invalid value of {0}'
                self._warnings.append(errmsg.format(ll))
                self.loglevel = 'INFO'

        LOGGING_CONFIG['loggers']['']['level'] = self.loglevel
        LOGGING_CONFIG['loggers']['dragonite']['level'] = self.loglevel
        self.verbose = bool(options.get('verbose', False))
        if self.verbose:
            LOGGING_CONFIG['handlers']['console']['formatter'] = 'normal'
        logging.config.dictConfig(LOGGING_CONFIG)

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
        self.nodb = options.get('nodb', False)

        self.comm = CommProxy(settings=self)

    @property
    def cache(self):
        if not hasattr(self, '_cache'):
            self._cache = DragoniteCache(tofile=self.use_cache)
        return self._cache

    def __str__(self):
        return '{0}'.format({
            'use_cache': self.use_cache,
        })

    @property
    def sms_enabled(self):
        return self.cache.get('send_sms', False)

    @property
    def email_enabled(self):
        return self.cache.get('send_email', False)

    @property
    def max_price(self):
        return self.cache.get('max_price', self.MAX_PRICE)

    @property
    def checkin(self):
        return self.cache.get('checkin', None)

    @property
    def checkout(self):
        return self.cache.get('checkout', None)

    @property
    def use_db(self):
        return (not self.nodb)

    def dict(self):
        config = OrderedDict()
        config['debug'] = self.debug
        config['info'] = self.info
        config['simple'] = self.simple
        config['use_cache'] = self.use_cache
        config['use_db'] = self.use_db
        config['max_attempts'] = self.max_attempts
        config['max_price'] = self.max_price
        config['checkin'] = self.checkin
        config['checkout'] = self.checkout
        config['loglevel'] = self.loglevel
        config['verbose'] = self.verbose
        config['sms_enabled'] = self.sms_enabled
        config['email_enabled'] = self.email_enabled
        return config

    def dumps(self, pretty=False):
        return jsonify(self.dict(), pretty=pretty)


settings = DragoniteConfig()
