#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import logging
import requests
import gevent.queue
import gevent.monkey
import gevent.pool
import gevent


def get_stream_logger(logname, loglevel=logging.DEBUG):
    # https://gist.github.com/neuroticnerd/7c60d61c8d9d9716f50d
    logger = logging.getLogger(logname)
    logger.propagate = False
    logger.setLevel(loglevel)
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
        )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def room_availability(log):
    global host_hotels
    global queue
    while True:
        try:
            hotel = queue.get(timeout=0)
            if not host_hotels[hotel]:
                break
            log.info('getting {0} availability'.format(hotel))
            gevent.sleep(1)
            queue.put(hotel)
        except gevent.queue.Empty:
            break


def dcbot():
    global pool_count
    global host_hotels
    global queue
    pool_count = 3
    host_hotels = {
        'hyatt': True,
        'hilton': True,
        'mariott': True,
    }
    try:
        log = get_stream_logger(__name__)
        gevent.monkey.patch_all()
        log.info('gevent monkey patching done')
        pool = gevent.pool.Pool(pool_count)
        log.info('gevent worker pool created with {0}'.format(pool_count))
        queue = gevent.queue.Queue()
        for h in host_hotels.keys():
            queue.put(h)
        log.info('host hotels added to task queue')
        #jobs = [pool.spawn(room_availability, h, log) for h in host_hotels]

        pool.spawn(room_availability, log)

        while not queue.empty() and not pool.free_count() == pool_count:
            gevent.sleep(0.1)
            for x in range(0, min(queue.qsize(), pool.free_count())):
                pool.spawn(room_availability, log)

        pool.join()
    except KeyboardInterrupt:
        host_hotels['hyatt'] = False
        host_hotels['hilton'] = False
        host_hotels['mariott'] = False
        pool.kill()
    log.info('dragoncon bot exiting\n')


if __name__ == '__main__':
    dcbot()
