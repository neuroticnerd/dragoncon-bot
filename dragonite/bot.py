#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import gevent.monkey
import gevent
import logging

from armory.environ import Environment

from .utils import get_stream_logger
from .hotels import ConHostHotels
from .dragoncon import DragonCon


class DragoniteConfig(object):
    levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARNING,
        'warning': logging.WARNING,
        'error': logging.ERROR,
    }

    def __init__(self, **options):
        self._warnings = []
        self.env = Environment({
            'DRAGONITE_LOGLEVEL': {'default': 'info'},
        })

        ll = options.get('loglevel', None)
        if ll is None:
            try:
                ll = self.env('DRAGONITE_LOGLEVEL')
                self.loglevel = self.levels[ll]
            except KeyError:
                errmsg = 'ignoring env var {0} with invalid value of {1}'
                self._warnings.append(errmsg.format('DRAGONITE_LOGLEVEL', ll))
                self.loglevel = logging.INFO
        else:
            try:
                self.loglevel = self.levels[ll]
            except KeyError:
                errmsg = 'ignoring option loglevel with invalid value of {0}'
                self._warnings.append(errmsg.format(ll))
                self.loglevel = logging.INFO


class DragonConBot(object):
    def __init__(self, config):
        self._config = config
        self._log = get_stream_logger(__name__, self._config.loglevel)

    def run(self):
        log = self._log
        for w in self._config._warnings:
            log.info(w)
        log.info('loglevel={0}'.format(
            logging.getLevelName(self._config.loglevel)))
        gevent.monkey.patch_all()
        log.info('gevent monkey patching done')
        tasks = []
        try:
            dcon = DragonCon()
            host_hotels = ConHostHotels(start=dcon.start, end=dcon.end)
            log.debug('spawning host hotel runner')
            tasks.append(gevent.spawn(host_hotels))
            log.debug('waiting for tasks to complete')
            gevent.wait(tasks)
        except KeyboardInterrupt:
            gevent.killall(tasks)
        log.info('dragoncon bot exiting\n')
