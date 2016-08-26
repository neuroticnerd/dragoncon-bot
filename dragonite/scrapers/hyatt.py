# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging

from bs4 import BeautifulSoup

import requests

from .base import HostHotelScraper, RequestsGuard

log = logging.getLogger(__name__)


class HyattAvailability(HostHotelScraper):
    name = 'hyatt'
    friendly = 'Hyatt Regency Atlanta'
    phone = '404-577-1234'
    link = 'https://atlanta.regency.hyatt.com/en/hotel/home.html'
    address = '265 Peachtree Street NE Atlanta, GA 30303'

    def scrape(self, result, rtimeout=8):
        """
        A large timeout is required because their redirects take a very
        long time to process and actually return a response
        """
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

        with RequestsGuard(result, __name__):
            # the request will redirect a number of times due to
            # how their site processes the search requests
            s = requests.Session()
            r = s.get(baseurl, timeout=rtimeout)
            r = s.get(searchurl, params=params, timeout=rtimeout)

            log.debug(self.msg('[HTTP {0}]'.format(r.status_code)))

            result.session = s
            result.response = r
            result.dom = BeautifulSoup(r.text, 'lxml')
            result.raw = r.text

        return result

    def parse(self, result, **kwargs):
        search_text = (
            'The hotel is not available for your requested travel dates.'
            ' It is either sold out or not yet open for reservations.'
        )
        not_available = False

        errors = result.dom.body.select('.error-block #msg .error')
        for error in errors:
            if not_available is True:
                break
            for text in error.findAll(text=True, recursive=False):
                if search_text in text.strip():
                    not_available = True
                    result.post_process = False
                    log.debug(self.msg('UNAVAILABLE'))
                    break

        if not errors and search_text in result.raw:
            errmsg = 'potential invalid detection of availability!'
            log.error(self.msg(errmsg))
            raise ValueError(errmsg)

        if not not_available:
            result.post_process = True
            log.debug(self.msg('post processing required'))

        result.available = not not_available

        return self
