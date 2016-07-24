# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import requests

from bs4 import BeautifulSoup

from .base import HostHotelScraper


class HyattAvailability(HostHotelScraper):
    name = 'hyatt'
    friendly = 'Hyatt Regency Atlanta'
    phone = '404-577-1234'
    link = 'https://atlanta.regency.hyatt.com/en/hotel/home.html'
    address = '265 Peachtree Street NE Atlanta, GA 30303'

    def scrape(self, result, *args, **kwargs):
        log = self.log
        # a large timeout is required because their redirects take a very
        # long time to process and actually return a response
        rtimeout = kwargs.get('timeout', 8)
        hyatturl = 'https://atlantaregency.hyatt.com'
        baseurl = '{hyatt}/en/hotel/home.html'.format(hyatt=hyatturl)
        searchurl = '{hyatt}/HICBooking'.format(hyatt=hyatturl)
        datefmt = '{0:%-m} {0:%y}'
        params = {
            'Lang': 'en',
            'accessibilityCheck': 'false',
            'adults': self.numppl,
            'childAge1': -1,
            'childAge2': -1,
            'childAge3': -1,
            'childAge4': -1,
            'corp_id': '',
            'day1': self.start.day,
            'day2': self.end.day,
            'kids': 0,
            'monthyear1': datefmt.format(self.start),
            'monthyear2': datefmt.format(self.end),
            'offercode': '',
            'pid': 'atlra',
            'rateType': 'Standard',
            'rooms': 1,
            'srcd': 'dayprop',
        }
        try:
            # the request will redirect a number of times due to
            # how their site processes the search requests
            s = requests.Session()
            result._session = s
            r = result.session.get(baseurl, timeout=rtimeout)
            r = result.session.get(searchurl, params=params, timeout=rtimeout)
            result._response = r
            log.debug(self.msg('[HTTP {0}]'.format(r.status_code)))
            result._dom = BeautifulSoup(r.text, 'lxml')
            result._raw = r.text
        except requests.exceptions.ReadTimeout:
            log.error(self.msg('TIMEOUT'))
        except requests.exceptions.ConnectionError:
            log.error(self.msg('CONNECTION ERROR'))

        return result

    def parse(self, result, **kwargs):
        log = self.log
        search_text = (
            'The hotel is not available for your requested travel dates.'
            ' It is either sold out or not yet open for reservations.'
        )

        errors = result.dom.body.select('.error-block #msg .error')
        for error in errors:
            if result.unavailable is True:
                break
            for text in error.findAll(text=True, recursive=False):
                if search_text in text.strip():
                    result.unavailable = True
                    result.post_process = False
                    log.debug(self.msg('UNAVAILABLE'))
                    break

        if not errors and search_text in result._raw:
            errmsg = 'potential invalid detection of availability!'
            log.error(self.msg(errmsg))
            raise ValueError(errmsg)

        if not result.unavailable:
            result.post_process = True
            log.debug(self.msg('post processing required'))

        result.available = not result.unavailable

        return self
