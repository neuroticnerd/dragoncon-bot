# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import timeit
from decimal import Decimal

from armory.gevent import patch_gevent_hub

import gevent
import gevent.monkey
from gevent.pool import Group
from gevent.queue import Queue

from . import beaker, scrapers
from .conf import settings
from .utils import LogAndForget


pool_size = 5
result_queue = Queue()
invocation = None
log = logging.getLogger(__name__)


def monkey_patch():
    patch_gevent_hub()
    gevent.monkey.patch_all()
    return True


class CrawlerGroup(Group):
    """ Normal gevent Group with extra method to determine greenlet status. """
    def alive(self):
        for greenlet in self.greenlets:
            if not greenlet.ready():
                return True
        return False


def check_room_availability(start, end):
    """
    Main point of entry into the coroutines.

    :param start: beginning date of availability window for hotel rooms.
    :type start: datetime.date
    :param end: ending date of availability window for hotel rooms.
    :type end: datetime.date

    NOTE: Normally we would want to share a SQLAlchemy session object,
    however, sessions are not intended to be shared across threads of
    execution. That is why new sessions are created in the coroutines.
    """
    if settings.use_db:
        global invocation
        beaker.init_database()
        session = beaker.create_session()
        invocation = beaker.Invocation(**settings.dict())
        session.add(invocation)
        session.commit()
        log.debug('invocation = {0}'.format(invocation))
        session.close()

    log.debug('spawning room availability monitors')
    hotel_scrapers = scrapers.get_scrapers(start, end)

    crawlers = CrawlerGroup()
    for scraper in hotel_scrapers:
        crawlers.spawn(_monitor_rooms, scraper)
    processor = gevent.spawn(_result_processor)

    crawlers.join()

    result_queue.put(StopIteration)
    processor.join(timeout=10)
    if not processor.ready():
        processor.kill()

    return crawlers


def _monitor_rooms(scraper):
    """
    Performs the actual scraping and parsing then adds results to the queue.

    :param scraper: the object holding the actual scraping and parsing code
    :type scraper: dragonite.scrapers.base.HostHotelScraper (or subclass)

    Depending on the settings configuration, it will also create a database
    entry containing the results of the run and iterate through additional
    runs up to ``max_attempts`` times.
    """
    log.info('checking {0} room availability...'.format(scraper.friendly))
    iteration = 0
    previous = None

    while settings.max_attempts == 0 or iteration < settings.max_attempts:
        if settings.max_attempts != 0:
            previous = timeit.default_timer()

        result = scraper()
        result.evaluate()

        if settings.use_db:
            session = beaker.create_session()
            entry = beaker.ScrapeResultEntry(
                hotel=result.parent.name,
                available=result.available,
                post_process=result.post_process,
                error=result.error,
                traceback=result.traceback,
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
        else:
            log.info('{0}: UNAVAILABLE'.format(scraper.friendly))

        result_queue.put(result)

        iteration += 1
        if settings.max_attempts != 0:
            elapsed = round(Decimal(timeit.default_timer() - previous), 4)
            sleeptime = max(0.1, (settings.interval - elapsed))
            gevent.sleep(sleeptime)

    return '{0}'.format(scraper.name)


def _result_processor():
    """
    Handles objects from ``result_queue`` until StopIteration is received.

    This processes the results of the scrapes, sending communications if
    availability was found and updating database entries when needed.
    """
    with settings.comm as gateway:
        for result in result_queue:
            log.debug('processing {0} result'.format(result.parent.friendly))

            entry = None
            if hasattr(result, 'entry'):
                entry = result.entry
                session = beaker.object_session(entry)

            if result.available and entry is not None:
                with LogAndForget('issue encountered notifying with uuid:'):
                    gateway.notify(result, entry.uuid)
                    entry.processed = True
                    session.commit()
                    log.debug('entry.processed = {0}'.format(entry.processed))
            elif result.available:
                with LogAndForget('issue encountered notifying:'):
                    gateway.notify(result)

            if entry is not None:
                session.close()

    return True
