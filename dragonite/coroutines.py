# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import timeit
import gevent.monkey
import gevent

from gevent.pool import Group, Pool
from gevent.queue import Queue
from decimal import Decimal
from armory.gevent import patch_gevent_hub
from dragonite import availability
from dragonite.conf import settings


pool_size = 5
processors = Pool(pool_size)
result_queue = Queue()
action_queue = Queue()


class CrawlerGroup(Group):
    def alive(self):
        for greenlet in self.greenlets:
            if not greenlet.ready():
                return True
        return False


def _monitor_rooms(scraper):
    log = settings.get_logger(__name__)
    log.info('monitoring {0} room availability...'.format(scraper.friendly))
    max_attempts = settings.max_attempts
    iteration = 0
    previous = timeit.default_timer()
    while max_attempts == 0 or iteration < max_attempts:
        try:
            scrape = [gevent.spawn(scraper)]
            gevent.wait(scrape)
            elapsed = round(Decimal(timeit.default_timer() - previous), 4)
            result_queue.put(scrape[0].value)
            sleeptime = settings.interval - max(0.1, elapsed)
            gevent.sleep(sleeptime)
            previous = timeit.default_timer()
        except:
            raise
        iteration += 1
    return '{0}'.format(scraper.name)


def _scrape_processor():
    log = settings.get_logger(__name__)
    result = result_queue.get()
    log.debug('_scrape_processor: {0}'.format(result))
    result.evaluate()
    if result.available:
        action_queue.put(result)
        return True
    return False


def _manage_worker_pool(crawlers):
    while crawlers.alive():
        # keep the worker pool filled
        for x in range(0, min(result_queue.qsize(), processors.free_count())):
            processors.spawn(_scrape_processor)
        # ensure context switches can happen
        gevent.sleep(0.1)


def monitor_room_availability(start, end):
    log = settings.get_logger(__name__)
    log.debug('spawning room availability monitors')
    hotel_scrapers = availability.get_scrapers(start, end)
    crawlers = CrawlerGroup()
    for scraper in hotel_scrapers:
        crawlers.spawn(_monitor_rooms, scraper)
    manager = gevent.spawn(_manage_worker_pool, crawlers)
    crawlers.join()
    if not result_queue.empty():
        processors.join(timeout=10)
        processors.kill()
    if not manager.ready():
        manager.kill()
    return crawlers


def monkey_patch():
    patch_gevent_hub()
    gevent.monkey.patch_all()
    return True


def killalltasks():
    # raise NotImplementedError()
    pass
