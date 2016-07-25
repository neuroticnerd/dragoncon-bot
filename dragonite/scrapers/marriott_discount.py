# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import requests

from bs4 import BeautifulSoup

from .base import HostHotelScraper


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

    def scrape(self, result, **kwargs):
        log = self.log
        rtimeout = kwargs.get('timeout', 5)
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

            # 'accountId': '',
            # 'corporateCode': '',
            # 'flexibleDateSearch': 'false',
            # 'flushSelectedRoomType': 'true',
            # 'groupCode': '',
            # 'includeNearByLocation': 'false',
            # 'isHwsGroupSearch': 'true',
            # 'isSearch': 'false',
            # 'marriottRewardsNumber': '',
            # 'miniStoreAvailabilitySear...': 'false',
            # 'numberOfGuests': self.numppl,
            # 'numberOfNights': 1,
            # 'numberOfRooms': 1,
            # 'propertyCode': 'atlmq',
            # 'useRewardsPoints': 'false',
        }
        try:
            s = requests.Session()
            result._session = s
            r = s.get(self.link, timeout=rtimeout)
            r = s.post(ratelist, params=params, timeout=rtimeout)
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
        log.debug([result._response.url] + result._response.history)
        unavailable = (
            'Sorry, there are no rooms remaining in the group block for a '
            'particular night. Please contact the Hotel directly for '
            'assistance.'
        )
        selector = '#popover-panel #unsuccessful-sell-popover'
        norooms = result.dom.body.select(selector)
        if norooms:
            result.unavailable = True
            result.post_process = False
            log.debug(self.msg('UNAVAILABLE'))
            norooms = norooms[0].get_text().strip()
            if unavailable not in norooms:
                errmsg = 'norooms present but unavailable not found'
                log.error(self.msg(errmsg))

        result.available = not result.unavailable

        return result
