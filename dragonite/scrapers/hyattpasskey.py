# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging

from bs4 import BeautifulSoup

import requests

from .base import HostHotelScraper, RequestsGuard

log = logging.getLogger(__name__)


class HyattPasskeyAvailability(HostHotelScraper):
    name = 'hyatt_passkey'
    friendly = 'Hyatt Regency Atlanta (passkey)'
    phone = '404-577-1234'
    link = 'https://atlanta.regency.hyatt.com/en/hotel/home.html'
    address = '265 Peachtree Street NE Atlanta, GA 30303'

    def scrape(self, result, rtimeout=8):
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

        with RequestsGuard(result, __name__):
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
            r = s.get(baseurl, timeout=rtimeout)
            r = s.post(groupurl, data=groupid, timeout=rtimeout)
            s.headers.update({
                'Referer': landingurl,
            })
            r = s.post(searchurl, data=payload, timeout=rtimeout)

            log.debug(self.msg('[HTTP {0}]'.format(r.status_code)))

            result.session = s
            result.response = r
            result.dom = BeautifulSoup(r.text, 'lxml')
            result.raw = r.text

        return result

    def parse(self, result, **kwargs):
        if 'maintenance/index.html' in result.response.url:
            result.error = True
            return result
        not_available = False

        search_text = 'No lodging matches your search criteria.'
        selector = '#main .shell #content .message-room'
        messages = result.dom.body.select(selector)
        for message in messages:
            if not_available is True:
                break
            for text in message.findAll(text=True, recursive=False):
                if search_text in text.strip():
                    not_available = True
                    result.post_process = False
                    log.debug(self.msg('UNAVAILABLE'))
                    break

        if not messages and search_text in result.raw:
            errmsg = 'potential invalid detection of availability!'
            log.error(self.msg(errmsg))
            raise ValueError(errmsg)

        if not not_available:
            result.post_process = True
            log.debug(self.msg('post processing required'))

        result.available = not not_available

        return result
