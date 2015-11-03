#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import requests

from bs4 import BeautifulSoup
from datetime import datetime
from unidecode import unidecode
from dateutil import parser


class DragonCon(object):
    def __init__(self):
        self._site_main = None

    @property
    def site_main(self):
        if self._site_main is None:
            try:
                r = requests.get('http://www.dragoncon.org/')
                self._site_main = BeautifulSoup(r.text)
            except:
                raise
        return self._site_main

    def get_event_dates(self):
        dateinfo = self.site_main.body.select('.region-countdown > div > h2')
        if len(dateinfo) != 1:
            raise ValueError('retrieved incorrect number of selected objects!')
        dateinfo = dateinfo[0].get_text()
        dateinfo = unidecode(dateinfo)
        datestop = dateinfo.split('-')[-1].strip().replace(',', '')
        datestart = dateinfo.split('-')[0].strip().replace(',', '')
        dateend = parser.parse(datestop)
        datestart = parser.parse('{0} {1}'.format(datestart, dateend.year))
        return (datestart.date(), dateend.date())
