# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import timeit
from decimal import Decimal

from armory.gevent import patch_gevent_hub

import gevent
import gevent.monkey
from gevent.pool import Group, Pool
from gevent.queue import Queue

from . import beaker, scrapers
from .conf import settings


pool_size = 5
processors = Pool(pool_size)
result_queue = Queue()
action_queue = Queue()
invocation = None


def monkey_patch():
    patch_gevent_hub()
    gevent.monkey.patch_all()
    return True


class CrawlerGroup(Group):
    def alive(self):
        for greenlet in self.greenlets:
            if not greenlet.ready():
                return True
        return False


def _monitor_rooms_old(scraper):
    log = logging.getLogger(__name__)
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
    log = logging.getLogger(__name__)
    log.info('checking {0} room availability...'.format(scraper.friendly))
    max_attempts = settings.max_attempts
    iteration = 0
    previous = None

    while max_attempts == 0 or iteration < max_attempts:
        if max_attempts != 0:
            previous = timeit.default_timer()
        try:
            result = scraper()
            result.evaluate()

            if settings.use_db:
                session = beaker.create_session()
                entry = beaker.ScrapeResultsEntry(
                    hotel=result.parent.name,
                    available=result.available,
                    post_process=result.post_process,
                    error=result.error,
                    raw=result.raw,
                    history='{0}'.format(
                        [
                            r.url for r in result.response.history
                        ] + [result.response.url]
                    ),
                    cookies='{0}'.format(result.session.cookies.get_dict()),
                )
                session.add(entry)
                session.commit()
                entry.session = session
                result.entry = entry

            if result.available:
                log.info('{0}: AVAILABILITY FOUND'.format(scraper.friendly))
                action_queue.put(result)
            else:
                log.info('{0}: UNAVAILABLE'.format(scraper.friendly))
        except:
            raise
        iteration += 1
        if max_attempts != 0:
            elapsed = round(Decimal(timeit.default_timer() - previous), 4)
            sleeptime = max(0.1, (settings.interval - elapsed))
            gevent.sleep(sleeptime)
    return '{0}'.format(scraper.name)


def _scrape_processor():
    log = logging.getLogger(__name__)
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
    log = logging.getLogger(__name__)

    with settings.comm as gateway:
        for action in action_queue:
            log.info('processing notifications for {0}'.format(
                action.parent.friendly
            ))
            gateway.notify(action)
            log.debug('_action_processor: {0}'.format(action))
            if hasattr(action, 'entry'):
                entry = action.entry
                session = entry.session
                entry.processed = True
                session.add(entry)
                session.commit()
                log.debug('entry.processed = {0}'.format(
                    action.entry.processed
                ))
                session.close()

    return True


def check_room_availability(start, end):
    log = logging.getLogger(__name__)
    log.debug('spawning room availability monitors')

    if settings.use_db:
        global invocation
        beaker.init_database()
        session = beaker.create_session()
        invocation = beaker.Invocation(**settings.dict())
        session.add(invocation)
        session.commit()
        log.info('invocation = {0}'.format(invocation.uuid))

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
