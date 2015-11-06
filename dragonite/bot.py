#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import gevent.monkey
import gevent

from .utils import get_stream_logger
from .hotels import ConHostHotels
from .dragoncon import DragonCon


class DragonConBot(object):
    def __init__(self):
        self._log = get_stream_logger(__name__)

    def run(self):
        log = self._log
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
