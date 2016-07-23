# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import requests

from bs4 import BeautifulSoup

from .base import HostHotelScraper


class HyattPasskeyAvailability(HostHotelScraper):
    name = 'hyatt_passkey'
    friendly = 'Hyatt Regency Atlanta (passkey)'
    phone = '404-577-1234'
    link = 'https://atlanta.regency.hyatt.com/en/hotel/home.html'
    address = '265 Peachtree Street NE Atlanta, GA 30303'

    def scrape(self, result, **kwargs):
        log = self.log
        rtimeout = kwargs.get('timeout', 8)
        hyatturl = 'https://aws.passkey.com/event/14179207/owner/323'
        baseurl = '{0}/home'.format(hyatturl)
        groupurl = '{0}/home/group'.format(hyatturl)
        landingurl = '{0}/landing'.format(hyatturl)
        searchurl = '{0}/rooms/select'.format(hyatturl)
        datefmt = '{0:%Y}-{0:%m}-{0:%d}'
        payload = {
            'hotelId': 323,
            'blockMap.blocks[0].blockId': 0,
            'blockMap.blocks[0].checkIn': datefmt.format(self.start),
            'blockMap.blocks[0].checkOut': datefmt.format(self.end),
            'blockMap.blocks[0].numberOfGuests': 4,
            'blockMap.blocks[0].numberOfRooms': 1,
            'blockMap.blocks[0].numberOfChildren': 0,
        }
        groupid = {
            'groupTypeId': 52445573,
        }

        try:
            # there are all sorts of redirects involved here because of the way
            # the site works to make sure necessary cookies and such are set
            s = requests.Session()
            s.headers.update({
                'User-Agent': (
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:43.0) '
                    'Gecko/20100101 Firefox/43.0'
                ),
                'Host': 'aws.passkey.com',
            })
            result._session = s
            r = s.get(baseurl, timeout=rtimeout)
            r = s.post(groupurl, data=groupid, timeout=rtimeout)
            s.headers.update({
                'Referer': landingurl,
            })
            r = s.post(searchurl, data=payload, timeout=rtimeout)

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
        if 'maintenance/index.html' in result.response.url:
            result.error = True
            return result

        search_text = 'No lodging matches your search criteria.'
        selector = '#main .shell #content .message-room'
        messages = result.dom.body.select(selector)
        for message in messages:
            if result.unavailable is True:
                break
            for text in message.findAll(text=True, recursive=False):
                if search_text in text.strip():
                    result.unavailable = True
                    result.post_process = False
                    log.debug(self.msg('UNAVAILABLE'))
                    break

        if not messages and search_text in result._raw:
            errmsg = 'potential invalid detection of availability!'
            log.error(self.msg(errmsg))
            raise ValueError(errmsg)

        if not result.unavailable:
            result.post_process = True
            log.debug(self.msg('post processing required'))

        return result
