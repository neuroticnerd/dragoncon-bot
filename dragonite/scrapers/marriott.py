# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging

from bs4 import BeautifulSoup

import requests

from .base import HostHotelScraper, RequestsGuard
from ..conf import settings

log = logging.getLogger(__name__)


class MarriottAvailability(HostHotelScraper):
    name = 'marriott'
    friendly = 'Atlanta Marriott Marquis'
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

        with RequestsGuard(result, __name__):
            s = requests.Session()
            r = s.get(home, timeout=rtimeout)
            r = s.get(search, params=params, timeout=rtimeout)

            log.debug(self.msg('[HTTP {0}]'.format(r.status_code)))

            result.session = s
            result.response = r
            result.dom = BeautifulSoup(r.text, 'lxml')
            result.raw = r.text

        return result

    def parse(self, result, **kwargs):
        unavailable = 'Sorry, currently there are no rooms available at this '
        unavailable += 'property for the dates you selected. '
        unavailable += 'Please try your search again'
        selector = '#popover-panel #no-rooms-available'
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

        if not not_available:
            selector = (
                'div.results-container div.room-rate-results '
                'div.rate-price .t-price'
            )
            rooms = result.dom.body.select(selector)
            lowest = None
            for room in rooms:
                price = float(room.get_text().strip().split()[0])
                log.debug(price)
                if lowest is None or price < lowest:
                    lowest = price
            if lowest is not None and lowest > settings.max_price:
                not_available = True
                msg = 'availability found but price too high ({0})'
                log.info(msg.format(lowest))

        result.available = not not_available

        return result
