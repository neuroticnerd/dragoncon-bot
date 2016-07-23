# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import requests

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

from .base import HostHotelScraper


class HiltonAvailability(HostHotelScraper):
    name = 'hilton'
    friendly = 'Hilton Atlanta'
    phone = '404-659-2000'
    link = 'http://www.atlanta.hilton.com/'
    address = '255 Courtland Street NE Atlanta, GA 30303'

    def scrape(self, result, **kwargs):
        log = self.log
        rtimeout = kwargs.get('timeout', 10)
        baseurl = 'http://www3.hilton.com'
        home = '{0}/en/hotels/georgia/hilton-atlanta-ATLAHHH/index.html'
        home = home.format(baseurl)
        search = '{0}/en_US/hi/search/findhotels/index.htm'.format(baseurl)
        datefmt = '{0:%d} {0:%b} {0:%Y}'
        params = {
            'arrivalDate': datefmt.format(self.start),
            'departureDate': datefmt.format(self.end),
            '_aaaRate': 'on',
            '_aarpRate': 'on',
            '_flexibleDates': 'on',
            '_governmentRate': 'on',
            '_seniorRate': 'on',
            '_travelAgencyRate': 'on',
            'bookButton': 'false',
            'corporateId': '',
            'ctyhocn': 'ATLAHHH',
            'groupCode': '',
            'numberOfAdults[0]': self.numppl,
            'numberOfAdults[1]': 1,
            'numberOfAdults[2]': 1,
            'numberOfAdults[3]': 1,
            'numberOfAdults[4]': 1,
            'numberOfAdults[5]': 1,
            'numberOfAdults[6]': 1,
            'numberOfAdults[7]': 1,
            'numberOfAdults[8]': 1,
            'numberOfChildren[0]': 0,
            'numberOfChildren[1]': 0,
            'numberOfChildren[2]': 0,
            'numberOfChildren[3]': 0,
            'numberOfChildren[4]': 0,
            'numberOfChildren[5]': 0,
            'numberOfChildren[6]': 0,
            'numberOfChildren[7]': 0,
            'numberOfChildren[8]': 0,
            'numberOfRooms': 1,
            'offerId': '',
            'promoCode': '',
            'roomKeyEnable': 'false',
            'searchQuery': '',
            'searchType': 'PROP',
        }
        try:
            # the post will redirect a number of times due to how their
            # site processes the search requests
            s = requests.Session()
            result._session = s
            r = s.get(home, timeout=rtimeout)
            r = s.post(search, params=params, timeout=rtimeout)
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
        unavailable = 'There are no rooms available for - at Hilton Atlanta'
        alert_selector = 'div#main_content div#main div.alertBox p'
        alertps = result.dom.body.select(alert_selector)
        alerts = []
        for alertp in alertps:
            errtext = alertp.findAll(text=True, recursive=False)
            errtext = [t.strip() for t in errtext if t.strip() != '']
            alerts.append(' '.join(errtext))
        for error in alerts:
            ratio = fuzz.ratio(error, unavailable)
            if ratio > 75:
                result.unavailable = True
                result.post_process = False
                log.debug(self.msg('UNAVAILABLE ({0}%)'.format(ratio)))

        return result
