# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import requests

from bs4 import BeautifulSoup

from .base import HostHotelScraper


class MariottAvailability(HostHotelScraper):
    name = 'mariott'
    friendly = 'Atlanta Mariott Marquis'
    phone = '404-521-0000'
    link = (
        'https://www.marriott.com/reservation/availability.mi'
        '?propertyCode=ATLmq&path=marriott&gc'
    )
    address = '265 Peachtree Center Avenue Atlanta, GA 30303'

    def scrape(self, result, **kwargs):
        log = self.log
        rtimeout = kwargs.get('timeout', 5)
        base = 'https://www.marriott.com'
        home = '{0}/hotels/travel/atlmq-atlanta-marriott-marquis/'.format(base)
        search = '{0}/reservation/availabilitySearch.mi'.format(base)
        params = {
            'fromDate': '{0:%m}/{0:%d}/{0:%Y}'.format(self.start),
            'toDate': '{0:%m}/{0:%d}/{0:%Y}'.format(self.end),
            'accountId': '',
            'clusterCode': 'none',
            'corporateCode': '',
            'dateFormatPattern': '',
            'flexibleDateSearch': 'false',
            'flushSelectedRoomType': 'true',
            'groupCode': '',
            'includeNearByLocation': 'false',
            'isHwsGroupSearch': 'true',
            'isSearch': 'false',
            'marriottRewardsNumber': '',
            'miniStoreAvailabilitySear...': 'false',
            'numberOfGuests': self.numppl,
            'numberOfNights': 1,
            'numberOfRooms': 1,
            'propertyCode': 'atlmq',
            'useRewardsPoints': 'false',
        }
        try:
            s = requests.Session()
            result._session = s
            r = s.get(home, timeout=rtimeout)
            r = s.get(search, params=params, timeout=rtimeout)
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
        unavailable = 'Sorry, currently there are no rooms available at this '
        unavailable += 'property for the dates you selected. '
        unavailable += 'Please try your search again'
        selector = '#popover-panel #no-rooms-available'
        norooms = result.dom.body.select(selector)
        if norooms:
            result.unavailable = True
            result.post_process = False
            log.debug(self.msg('UNAVAILABLE'))
            norooms = norooms[0].get_text().strip()
            if unavailable not in norooms:
                errmsg = 'norooms present but unavailable not found'
                log.error(self.msg(errmsg))
                raise ValueError(errmsg)
        return result
