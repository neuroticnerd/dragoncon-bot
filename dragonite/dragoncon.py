# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import gevent.monkey
import gevent.queue
import gevent.pool
import gevent
import requests
import dateutil.parser
import timeit

from collections import OrderedDict
from bs4 import BeautifulSoup
from unidecode import unidecode
from decimal import Decimal
from armory.serialize import jsonify

from .conf import settings
from dragonite import scraping


class DragonCon(object):
    site_url = 'http://www.dragoncon.org/'

    def __init__(self, interval=1):
        self._log = settings.get_logger(__name__)
        self._site_main = None
        self.dates_selector = '.region-countdown > div > h2'
        self.interval = interval

    def run(self):
        log = self._log
        try:
            dcstr = '{0}'.format(self.event_info())
            log.info(dcstr)
        except KeyboardInterrupt:
            pass
        except requests.exceptions.ConnectionError as e:
            log.debug('{0}'.format(e))
            log.error('connection error! now aborting!')
        log.info('dragoncon bot exiting\n')

    def monitor_room_availability(self):
        log = self._log
        for w in settings._warnings:
            log.info(w)
        gevent.monkey.patch_all()
        log.info('gevent monkey patching done')
        tasks = []
        try:
            log.debug('spawning host hotel runner')
            tasks.append(gevent.spawn(self))
            log.debug('waiting for tasks to complete')
            gevent.wait(tasks)
        except KeyboardInterrupt:
            gevent.killall(tasks)
        except requests.exceptions.ConnectionError as e:
            log.debug('{0}'.format(e))
            log.error('connection error! now aborting!')
            gevent.killall(tasks)
        log.info('dragoncon bot exiting\n')

    def get_room_availability(self):
        log = self._log
        log.debug('runonce check not implemented')

    @property
    def site_main(self):
        if self._site_main is None:
            try:
                r = requests.get('http://www.dragoncon.org/')
                self._site_main = BeautifulSoup(r.text, 'lxml')
            except:
                raise
        return self._site_main

    @property
    def start(self):
        if not hasattr(self, '_start'):
            self._populate_dates()
        return self._start

    @property
    def end(self):
        if not hasattr(self, '_end'):
            self._populate_dates()
        return self._end

    def _populate_dates(self):
        log = self._log
        domdate = self.site_main.body.select(self.dates_selector)
        domlen = len(domdate)
        if domlen != 1:
            errmsg = "incorrect number of objects ({0}) returned from '{1}'"
            raise ValueError(errmsg.format(domlen, self.dates_selector))
        dateinfo = unidecode(domdate[0].get_text())
        parts = [p.strip().replace(',', ' ') for p in dateinfo.split('-')]
        parts = [' '.join(p.split()) for p in parts]
        log.debug(parts)
        numparts = len(parts)
        if numparts != 2:
            errmsg = "incorrect number of dates detected: {0} from {1}"
            errmsg = errmsg.format(numparts, parts)
            log.error(errmsg)
            raise ValueError(errmsg)
        self._start = dateutil.parser.parse(parts[0]).date()
        self._end = dateutil.parser.parse(parts[1]).date()
        self._start = self._start.replace(year=self._end.year)
        log.info("start date: {0}".format(self._start))
        log.info("  end date: {0}".format(self._end))
        if settings.cache:
            # do caching things
            pass

    def event_info(self):
        info = OrderedDict()
        info['con'] = 'Dragon Con'
        info['url'] = self.site_url
        info['start'] = self.start
        info['end'] = self.end
        return '{0}'.format(jsonify(info))

    def __call__(self):
        log = self._log
        hotels = []
        try:
            log.debug('spawning room availability monitors')
            hotels.append(gevent.spawn(
                self._monitor_rooms, 'hyatt',
                scraping.hyatt_room_availability))
            hotels.append(gevent.spawn(
                self._monitor_rooms, 'hilton',
                scraping.hilton_room_availability))
            hotels.append(gevent.spawn(
                self._monitor_rooms, 'mariott',
                scraping.mariott_room_availability))
            log.debug('waiting for room availability monitoring to complete')
            gevent.wait(hotels)
        except Exception as e:
            log.error(e)
            gevent.killall(hotels)
        log.info([h.value for h in hotels])

    def _monitor_rooms(self, friendly, availability_func):
        log = self._log
        log.info('monitoring {0} room availability'.format(friendly))
        previous = timeit.default_timer()
        while True:
            try:
                checks = []
                checks.append(gevent.spawn(
                    availability_func, log,
                    self.start, self.end))
                gevent.wait(checks)
                elapsed = round(Decimal(timeit.default_timer() - previous), 4)
                sleeptime = self.interval - max(0.1, elapsed)
                gevent.sleep(sleeptime)
                dbgmsg = 'func({0}), loop({1})'
                log.debug(dbgmsg.format(
                    checks[0].value['time'],
                    round(timeit.default_timer() - previous, 4)))
                previous = timeit.default_timer()
                log.error(checks[0].value)
            except:
                raise
        return '{0}'.format(friendly)
