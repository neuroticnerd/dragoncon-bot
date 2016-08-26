# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging

from bs4 import BeautifulSoup

import requests

from .base import HostHotelScraper, RequestsGuard

log = logging.getLogger(__name__)


class MarriottDiscountAvailability(HostHotelScraper):
    name = 'marriott_discount'
    friendly = 'Atlanta Marriott Marquis (group rate)'
    phone = '404-521-0000'
    link = (
        'https://www.marriott.com/meeting-event-hotels/group-corporate-travel'
        '/groupCorp.mi?resLinkData=Dragon%20Con%202016'
        '%5Eatlmq%60dradraa%7Cdradrad%7Cdradrat%7Cdradraq%7Cdradrap'
        '%60229.00-400.00%60USD%60false%604%6009/01/16%6009/05/16%6008/10/16&'
        'app=resvlink&stop_mobi=yes'
    )
    address = '265 Peachtree Center Avenue Atlanta, GA 30303'

    def scrape(self, result, rtimeout=5):
        base = 'https://www.marriott.com'
        ratelist = '{0}/meetings/rateListMenu.mi'.format(base)
        params = {
            'fromDate': '{0:%m}/{0:%d}/{0:%y}'.format(self.start),
            'toDate': '{0:%m}/{0:%d}/{0:%y}'.format(self.end),
            'numberOfRooms': self.numrooms,
            'guestsPerRoom': self.numppl,
            'dateFormatPattern': 'MM/dd/yy',
            'dateFormatPattern': 'MM/dd/yy',
            'cutOffDate': '08/10/16',
            'clusterCode': 'group',
            'corp': 'false',
            'defaultToDateDays': 1,
            'groupCorpCodes[]': 'dradraa',
            'groupCorpCodes[]': 'dradrad',
            'groupCorpCodes[]': 'dradrat',
            'groupCorpCodes[]': 'dradraq',
            'groupCorpCodes[]': 'dradrap',
            'marshaCode': 'atlmq',
            'maxDate': '09/05/2016',
            'minDate': '09/01/2016',
            'monthNames': (
                'January,February,March,April,May,June,July,'
                'August,September,October,November,December'
            ),
            'populateTodateFromFromDate': 'true',
            'single-search-date-format': 'mm/dd/yy',
            'weekDays': 'S,M,T,W,T,F,S',
        }

        with RequestsGuard(result, __name__):
            s = requests.Session()
            r = s.get(self.link, timeout=rtimeout)
            r = s.post(ratelist, params=params, timeout=rtimeout)

            log.debug(self.msg('[HTTP {0}]'.format(r.status_code)))

            result.session = s
            result.response = r
            result.dom = BeautifulSoup(r.text, 'lxml')
            result.raw = r.text

        return result

    def parse(self, result, **kwargs):
        unavailable = (
            'Sorry, there are no rooms remaining in the group block for a '
            'particular night. Please contact the Hotel directly for '
            'assistance.'
        )
        selector = '#popover-panel #unsuccessful-sell-popover'
        not_available = False

        norooms = result.dom.body.select(selector)
        if norooms:
            not_available = True
            result.post_process = False
            log.debug(self.msg('UNAVAILABLE'))
            norooms = norooms[0].get_text().strip()
            if unavailable not in norooms:
                errmsg = 'norooms present but unavailable not found'
                log.error(self.msg(errmsg))

        result.available = not not_available

        return result
