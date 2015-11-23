#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import gevent.monkey
import gevent
import requests
import dateutil.parser

from bs4 import BeautifulSoup
from unidecode import unidecode

from .hotels import ConHostHotels
from .conf import settings


class DragonConBot(object):
    def __init__(self):
        self._log = settings.get_logger(__name__)
        self.dragoncon = DragonCon()

    def run(self):
        log = self._log
        try:
            dcstr = '{0}'.format(self.dragoncon)
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
            host_hotels = ConHostHotels(
                self.dragoncon.start,
                self.dragoncon.end
            )
            log.debug('spawning host hotel runner')
            tasks.append(gevent.spawn(host_hotels))
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


class DragonCon(object):
    site_url = 'http://www.dragoncon.org/'

    def __init__(self):
        self._log = settings.get_logger(__name__)
        self._site_main = None
        self._start = None
        self._end = None
        self._dates_selector = '.region-countdown > div > h2'

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
        if self._start is None:
            self._populate_dates()
        return self._start

    @property
    def end(self):
        if self._end is None:
            self._populate_dates()
        return self._end

    def _populate_dates(self):
        log = self._log
        domdate = self.site_main.body.select(self._dates_selector)
        domlen = len(domdate)
        if domlen != 1:
            errmsg = "incorrect number of objects ({0}) returned from '{1}'"
            raise ValueError(errmsg.format(domlen, self._dates_selector))
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

    def __str__(self):
        return '{0}'.format({
            'url': self.site_url,
            'start': self.start,
            'end': self.end,
        })
