#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import logging

from armory.environ import Environment


class DragoniteConfig(object):
    levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARNING,
        'warning': logging.WARNING,
        'error': logging.ERROR,
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

        self.loglevelname = logging.getLevelName(self.loglevel)

        cc = options.get('cache', None)
        if cc is None:
            self.cache = False
        else:
            self.cache = bool(cc)

        self.verbose = bool(options.get('verbose', False))

    def __str__(self):
        return '{0}'.format({
            'loglevel': self.loglevelname,
            'cache': self.cache,
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

settings = DragoniteConfig()
