# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import requests
import dateutil.parser

from collections import OrderedDict
from bs4 import BeautifulSoup
from unidecode import unidecode
from armory.serialize import jsonify

from dragonite import coroutines
from dragonite.conf import settings


class DragonCon(object):
    site_url = 'http://www.dragoncon.org/'

    def __init__(self, interval=1):
        self._log = settings.get_logger(__name__)
        self._site_main = None
        self.dates_selector = '.region-countdown > div > h2'
        self.interval = interval

    def __call__(self):
        log = self._log
        hotels = [coroutines.monitor_room_availability()]
        log.info([h.value for h in hotels])

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

    def hotel_availability(self):
        log = self._log
        for w in settings._warnings:
            log.info(w)
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

    def event_dates(self):
        log = self._log
        domdate = self.site_content.body.select(self.dates_selector)
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
