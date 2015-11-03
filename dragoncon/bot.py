#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import requests
import gevent.queue
import gevent.monkey
import gevent.pool
import gevent

from .utils import get_stream_logger
from .host_hotels import room_availability
from .dragoncon import DragonCon


class DragonConBot(object):
    def __init__(self, pool_count=3):
        self.log = get_stream_logger(__name__)
        self.pool_count = pool_count
        self.host_hotels = {
            'hyatt': True,
            'hilton': True,
            'mariott': True,
        }

    def run(self):
        log = self.log
        gevent.monkey.patch_all()
        log.info('gevent monkey patching done')
        pool = gevent.pool.Pool(self.pool_count)
        log.info('gevent worker pool created with {0}'.format(self.pool_count))
        queue = gevent.queue.Queue()
        for h in self.host_hotels.keys():
            queue.put(h)
        log.info('host hotels added to task queue')
        try:
            dcon = DragonCon()
            eventstart, eventstop = dcon.get_event_dates()
            log.info('dragoncon start = {0}'.format(eventstart))
            log.info('dragoncon stop  = {0}'.format(eventstop))
        except:
            raise
        try:
            pool.spawn(room_availability, log, self.host_hotels, queue)
            while not queue.empty() and not pool.free_count() == self.pool_count:
                gevent.sleep(0.1)
                for x in range(0, min(queue.qsize(), pool.free_count())):
                    pool.spawn(room_availability, log, self.host_hotels, queue)
            pool.join()
        except KeyboardInterrupt:
            self.host_hotels['hyatt'] = False
            self.host_hotels['hilton'] = False
            self.host_hotels['mariott'] = False
            pool.kill()
        log.info('dragoncon bot exiting\n')
