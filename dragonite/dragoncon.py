# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
from collections import OrderedDict

from armory.serialize import jsonify

from bs4 import BeautifulSoup

import dateutil.parser

import requests

from unidecode import unidecode

from . import coroutines
from .conf import settings


class DragonCon(object):
    site_url = 'http://www.dragoncon.org/'

    def __init__(self, interval=1):
        self._log = logging.getLogger(__name__)
        self._site_main = None
        self.dates_selector = '.region-countdown > div > h2'
        self.interval = interval

    def __call__(self, runme=True):
        return self.run(info_only=(not runme))

    @property
    def site_content(self):
        if self._site_main is None:
            r = requests.get('http://www.dragoncon.org/')
            self._site_main = BeautifulSoup(r.text, 'lxml')
        return self._site_main

    @property
    def start(self):
        if not hasattr(self, '_start'):
            self.event_dates()
        return self._start

    @property
    def end(self):
        if not hasattr(self, '_end'):
            self.event_dates()
        return self._end

    @property
    def event_info(self):
        info = OrderedDict()
        info['con'] = 'Dragon Con'
        info['url'] = self.site_url
        info['start'] = self.start
        info['end'] = self.end
        return '{0}'.format(jsonify(info))

    @property
    def event_info_pretty(self):
        info_template = (
            '*------------------------*\n'
            '|     DragonCon {year}     |\n'
            '| start date: {start} |\n'
            '|   end date: {end} |\n'
            '*------------------------*'
        )
        return info_template.format(
            year=self.start.year,
            start=self.start,
            end=self.end
        )

    @property
    def checkin(self):
        if settings.checkin is not None:
            value = dateutil.parser.parse(settings.checkin).date()
        else:
            value = self.start
        return value

    @property
    def checkout(self):
        if settings.checkout is not None:
            value = dateutil.parser.parse(settings.checkout).date()
        else:
            value = self.end
        return value

    def event_dates(self):
        log = self._log
        try:
            self._start = settings.cache['event_start']
            self._end = settings.cache['event_end']
            return
        except KeyError:
            log.debug('retrieving event dates...')
        domdate = self.site_content.body.select(self.dates_selector)
        domlen = len(domdate)
        if domlen != 1:
            errmsg = "incorrect number of objects ({0}) returned from '{1}'"
            raise ValueError(errmsg.format(domlen, self.dates_selector))
        dateinfo = unidecode(domdate[0].get_text())
        parts = [p.strip().replace(',', ' ') for p in dateinfo.split('-')]
        parts = [' '.join(p.split()[:2]) for p in parts]
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
        log.debug("start date: {0}".format(self._start))
        log.debug("  end date: {0}".format(self._end))
        settings.cache['event_start'] = self.start
        settings.cache['event_end'] = self.end
        settings.cache.flush()

    def run(self, info_only=False):
        log = self._log
        for w in settings._warnings:
            log.warning(w)
        coroutines.monkey_patch()
        log.debug('gevent monkey patching done')

        try:
            log.debug('fetching event info...')
            dcstr = '{0}'.format(self.event_info)
            log.debug(dcstr)
            if info_only:
                log.debug('info only; terminating')
                return True
            log.debug('spawning tasks...')
            hotels = coroutines.check_room_availability(
                self.checkin,
                self.checkout
            )
            log.debug([h.value for h in hotels])
        except KeyboardInterrupt:
            log.error('terminating program due to KeyboardInterrupt')
        except requests.exceptions.ConnectionError as e:
            log.debug('{0}'.format(e))
            log.error('internet connection error; aborting!')
        log.info('dragoncon bot exiting\n')
