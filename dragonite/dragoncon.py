#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import requests
import dateutil.parser

from bs4 import BeautifulSoup
from unidecode import unidecode


class DragonCon(object):
    site_url = 'http://www.dragoncon.org/'

    def __init__(self, config):
        self._config = config
        self._log = self._config.get_logger(__name__)
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
        if self._config.cache:
            # do caching things
            pass

    def __str__(self):
        return '{0}'.format({
            'url': self.site_url,
            'start': self.start,
            'end': self.end,
        })
