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
scrapers = {
    'hyatt': 'hyatt',
    'hyatt.passkey': 'hyatt_passkey',
    'hilton': 'hilton',
    'mariott': 'mariott',
}
latest_results = {
    key: None for key in scrapers.keys()
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


def _monitor_rooms(friendly, availability_func, obj):
    log = settings.get_logger(__name__)
    log.info('monitoring {0} room availability'.format(friendly))
    previous = timeit.default_timer()
    while True:
        try:
            checks = []
            checks.append(gevent.spawn(
                availability_func, obj))
            gevent.wait(checks)
            elapsed = round(Decimal(timeit.default_timer() - previous), 4)
            sleeptime = settings.interval - max(0.1, elapsed)
            gevent.sleep(sleeptime)
            log.debug(checks[0].value)
            # log.debug('func({0}), loop({1})'.format(
            #     checks[0].value['time'],
            #     round(timeit.default_timer() - previous, 4))
            # )
            previous = timeit.default_timer()
            log.error(checks[0].value)
        except:
            raise
    return '{0}'.format(friendly)


def monitor_room_availability(start, end):
    log = settings.get_logger(__name__)
    availability = []
    runner = scraping.RoomAvailability(start, end)
    try:
        log.debug('spawning room availability monitors')
        availability = [
            gevent.spawn(
                _monitor_rooms, name, getattr(runner, func), runner
            ) for name, func in scrapers.items()
        ]
        log.debug('waiting for room availability monitoring to complete')
        gevent.wait(availability)
    except Exception as e:
        log.error(e)
        gevent.killall(availability)
        raise
    return availability
