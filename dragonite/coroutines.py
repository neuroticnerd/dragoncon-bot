# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import gevent.monkey
import gevent
import timeit

from armory.gevent import patch_gevent_hub
from decimal import Decimal
from gevent.pool import Group, Pool
from gevent.queue import Queue

from dragonite import scrapers
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


def _monitor_rooms_old(scraper):
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


def _monitor_rooms(scraper):
    log = settings.get_logger(__name__)
    log.info('monitoring {0} room availability...'.format(scraper.friendly))
    max_attempts = settings.max_attempts
    iteration = 0
    while max_attempts == 0 or iteration < max_attempts:
        try:
            result = scraper()
            result.evaluate()

            if result.post_process:
                selector = (
                    '#content-container > #main-col > '
                    '#rates_and_rooms_container'
                )
                content = result.dom.body.select(selector)
                # log.debug(content[0].prettify())
                # log.debug(result.dom.body.select('#room_type_container')[0].prettify())
            if result.available:
                log.debug('{0}: AVAILABILITY FOUND')
                action_queue.put(result)
            else:
                log.debug('{0}: UNAVAILABLE')
            gevent.sleep(0.1)
        except:
            raise
        iteration += 1
    return '{0}'.format


def _scrape_processor():
    log = settings.get_logger(__name__)
    result = result_queue.get()
    log.debug('_scrape_processor: {0}'.format(result))
    result.evaluate()
    if result.post_process:
        selector = (
            '#content-container > #main-col > #rates_and_rooms_container'
        )
        content = result.dom.body.select(selector)
        # log.debug(content[0].prettify())
        # log.debug(result.dom.body.select('#room_type_container')[0].prettify())
    if result.available:
        action_queue.put(result)
        return True
    return False


def _manage_processor_pool(crawlers):
    while crawlers.alive() or not result_queue.empty():
        # keep the worker pool filled
        for x in range(0, min(result_queue.qsize(), processors.free_count())):
            processors.spawn(_scrape_processor)
        # ensure context switches can happen
        gevent.sleep(0.1)


def _action_processor():
    log = settings.get_logger(__name__)
    with settings.comm as gateway:
        for action in action_queue:
            gateway.notify(action)
            log.debug('_action_processor: {0}'.format(action))
    return True


def monitor_room_availability(start, end):
    log = settings.get_logger(__name__)
    log.debug('spawning room availability monitors')
    hotel_scrapers = scrapers.get_scrapers(start, end)
    crawlers = CrawlerGroup()
    for scraper in hotel_scrapers:
        crawlers.spawn(_monitor_rooms, scraper)
    manager = gevent.spawn(_manage_processor_pool, crawlers)
    mailman = gevent.spawn(_action_processor)
    crawlers.join()
    if not result_queue.empty():
        manager.join(timeout=10)
        processors.kill()
    if not manager.ready():
        manager.kill()
    action_queue.put(StopIteration)
    mailman.join(timeout=10)
    if not mailman.ready():
        mailman.kill()
    return crawlers


def monkey_patch():
    patch_gevent_hub()
    gevent.monkey.patch_all()
    return True


def killalltasks():
    # raise NotImplementedError()
    pass
