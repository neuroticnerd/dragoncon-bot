#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import timeit
import gevent.monkey
import gevent.queue
import gevent.pool
import gevent

from decimal import Decimal
from dragonite import scraping
from dragonite.conf import settings


response_queue = gevent.queue.Queue()
response_map = {
    'hyatt': 'parse_hyatt_response',
    'hyatt.passkey': 'parse_hyatt_passkey',
    'mariott': 'parse_mariott_response',
    'hilton': 'parse_hilton_response',
}


def killalltasks():
    raise NotImplementedError()


def monkey_patch():
    gevent.monkey.patch_all()
    return True


def response_processor():
    r = response_queue.pop()
    origin = r['origin']
    response_map[origin](r['data'])


def _monitor_rooms(friendly, availability_func, start, end):
    log = settings.get_logger(__name__)
    log.info('monitoring {0} room availability'.format(friendly))
    previous = timeit.default_timer()
    while True:
        try:
            checks = []
            checks.append(gevent.spawn(
                availability_func, log,
                start, end))
            gevent.wait(checks)
            elapsed = round(Decimal(timeit.default_timer() - previous), 4)
            sleeptime = settings.interval - max(0.1, elapsed)
            gevent.sleep(sleeptime)
            dbgmsg = 'func({0}), loop({1})'
            log.debug(checks[0].value)
            log.debug(dbgmsg.format(
                checks[0].value['time'],
                round(timeit.default_timer() - previous, 4)))
            previous = timeit.default_timer()
            log.error(checks[0].value)
        except:
            raise
    return '{0}'.format(friendly)


def monitor_room_availability(start, end):
    log = settings.get_logger(__name__)
    try:
        log.debug('spawning room availability monitors')
        hotels = (
            gevent.spawn(
                _monitor_rooms, 'hyatt',
                scraping.hyatt_room_availability,
                start, end
            ),
            gevent.spawn(
                _monitor_rooms, 'hilton',
                scraping.hilton_room_availability,
                start, end
            ),
            gevent.spawn(
                _monitor_rooms, 'mariott',
                scraping.mariott_room_availability,
                start, end
            ),
        )
        log.debug('waiting for room availability monitoring to complete')
        gevent.wait(hotels)
    except Exception as e:
        log.error(e)
        gevent.killall(hotels)
    return hotels
