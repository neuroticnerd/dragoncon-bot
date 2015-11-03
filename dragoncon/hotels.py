#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import gevent.queue
import gevent.pool
import gevent
import requests
import timeit

from decimal import Decimal
from bs4 import BeautifulSoup
from .utils import get_stream_logger, timed_function


class ConHostHotels(object):
    def __init__(self, start, end, interval=1):
        self._log = get_stream_logger(__name__)
        self._start = start
        self._end = end
        self.interval = interval

    def __call__(self):
        log = self._log
        hotels = []
        try:
            log.debug('spawning room availability monitors')
            hotels.append(gevent.spawn(
                self._monitor_rooms, 'hyatt',
                self.hyatt_room_availability))
            hotels.append(gevent.spawn(
                self._monitor_rooms, 'hilton',
                self.hilton_room_availability))
            hotels.append(gevent.spawn(
                self._monitor_rooms, 'mariott',
                self.mariott_room_availability))
            log.debug('waiting for room availability monitoring to complete')
            gevent.wait(hotels)
        except Exception as e:
            log.error(e)
            gevent.killall(hotels)
        log.debug([h.value for h in hotels])

    def _monitor_rooms(self, friendly, availability_func):
        log = self._log
        log.debug('monitoring {0} room availability'.format(friendly))
        previous = timeit.default_timer()
        while True:
            try:
                checks = []
                checks.append(gevent.spawn(
                    availability_func, log,
                    self._start, self._end))
                gevent.wait(checks)
                elapsed = round(Decimal(timeit.default_timer() - previous), 4)
                sleeptime = self.interval - max(0.1, elapsed)
                gevent.sleep(sleeptime)
                dbgmsg = 'func({0}), loop({1})'
                log.debug(dbgmsg.format(
                    checks[0].value['time'],
                    round(timeit.default_timer() - previous, 4)))
                previous = timeit.default_timer()
            except:
                raise
        return '{0}'.format(friendly)

    @timed_function
    def hyatt_room_availability(self, log, start, end, numppl=4):
        # a large timeout is required because their redirects take a very
        # long time to process and actually return a response
        rtimeout = 20
        hyatturl = 'https://atlantaregency.hyatt.com'
        baseurl = '{hyatt}/en/hotel/home.html'.format(hyatt=hyatturl)
        searchurl = '{hyatt}/HICBooking'.format(hyatt=hyatturl)
        unavailable = 'The hotel is not available for your requested travel dates.'
        try:
            s = requests.session()
            r = s.get(baseurl, timeout=rtimeout)
            search = {
                'Lang': 'en',
                'accessibilityCheck': 'false',
                'adults': numppl,
                'childAge1': -1,
                'childAge2': -1,
                'childAge3': -1,
                'childAge4': -1,
                'corp_id': '',
                'day1': start.day,
                'day2': end.day,
                'kids': 0,
                'monthyear1': '{0:%-m} {0:%y}'.format(start),
                'monthyear2': '{0:%-m} {0:%y}'.format(end),
                'offercode': '',
                'pid': 'atlra',
                'rateType': 'Standard',
                'rooms': 1,
                'srcd': 'dayprop',
            }

            # this will redirect up to two times because of how their site works
            r = s.get(searchurl, params=search, timeout=rtimeout)
            log.debug('[hyatt:rooms] [{0}]'.format(r.status_code))
            results = BeautifulSoup(r.text, 'lxml')
            errors = results.body.select('.error-block #msg .error')
            if errors:
                for err in errors:
                    errtext = [
                        t.strip() for t in err.findAll(text=True, recursive=False)
                        if t.strip() != '']
                    errtext = errtext[0] if len(errtext) > 0 else '<unavailable>'
                    log.debug('ERROR: {0}'.format(errtext))
                log.debug('[hyatt:rooms] UNAVAILABLE')
            else:
                if unavailable in r.text:
                    raise ValueError('invalid detection of availability!')
                log.debug('[hyatt:rooms] AVAILABLE')
        except requests.exceptions.ReadTimeout:
            log.debug('[hyatt:rooms] TIMEOUT')
        return {'stuff': 'things'}

    @timed_function
    def hilton_room_availability(self, log, start, end):
        log.debug('HILTON')
        return {'stuff': 'things'}

    @timed_function
    def mariott_room_availability(self, log, start, end):
        log.debug('MARIOTT')
        return {'stuff': 'things'}
