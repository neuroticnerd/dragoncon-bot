# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import timeit
import gevent.monkey
import gevent.queue
import gevent.pool
import gevent

from decimal import Decimal
from dragonite import availability
from dragonite.conf import settings


response_queue = gevent.queue.Queue()
scrapers = {
    'hyatt': availability.HyattAvailability,
    'hyatt_passkey': availability.HyattPasskeyAvailability,
    'hilton': availability.HiltonAvailability,
    'mariott': availability.MariottAvailability,
}
latest_results = {
    key: None for key in scrapers.keys()
}


def killalltasks():
    raise NotImplementedError()


def monkey_patch():
    gevent.monkey.patch_all()
    return True


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
            previous = timeit.default_timer()
            log.error(checks[0].value)
            response_queue.push(checks[0].value)
        except:
            raise
    return '{0}'.format(friendly)


def monitor_room_availability(start, end):
    log = settings.get_logger(__name__)
    hotels = []
    try:
        log.debug('spawning room availability monitors')
        hotels = [
            gevent.spawn(
                _monitor_rooms, name, callable_object
            ) for name, callable_object in scrapers.items()
        ]
        log.debug('waiting for room availability monitoring to complete')
        gevent.wait(hotels)
    except Exception as e:
        log.error(e)
        gevent.killall(hotels)
        raise
    return hotels
