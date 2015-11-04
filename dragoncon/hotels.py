#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import gevent.queue
import gevent.pool
import gevent
import requests
import timeit

from decimal import Decimal
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from .utils import get_stream_logger, timed_function


class ConHostHotels(object):
    def __init__(self, start, end, interval=1):
        self._log = get_stream_logger(__name__)
        self._start = start
        self._end = end
        self.interval = interval

    def __call__(self):
        log = self._log
        hotels = []
        try:
            log.debug('spawning room availability monitors')
            hotels.append(gevent.spawn(
                self._monitor_rooms, 'hyatt',
                self.hyatt_room_availability))
            hotels.append(gevent.spawn(
                self._monitor_rooms, 'hilton',
                self.hilton_room_availability))
            hotels.append(gevent.spawn(
                self._monitor_rooms, 'mariott',
                self.mariott_room_availability))
            log.debug('waiting for room availability monitoring to complete')
            gevent.wait(hotels)
        except Exception as e:
            log.error(e)
            gevent.killall(hotels)
        log.debug([h.value for h in hotels])

    def _monitor_rooms(self, friendly, availability_func):
        log = self._log
        log.debug('monitoring {0} room availability'.format(friendly))
        previous = timeit.default_timer()
        while True:
            try:
                checks = []
                checks.append(gevent.spawn(
                    availability_func, log,
                    self._start, self._end))
                gevent.wait(checks)
                elapsed = round(Decimal(timeit.default_timer() - previous), 4)
                sleeptime = self.interval - max(0.1, elapsed)
                gevent.sleep(sleeptime)
                dbgmsg = 'func({0}), loop({1})'
                log.debug(dbgmsg.format(
                    checks[0].value['time'],
                    round(timeit.default_timer() - previous, 4)))
                previous = timeit.default_timer()
            except:
                raise
        return '{0}'.format(friendly)

    @timed_function
    def hyatt_room_availability(self, log, start, end, numppl=4):
        # a large timeout is required because their redirects take a very
        # long time to process and actually return a response
        rtimeout = 20
        hyatturl = 'https://atlantaregency.hyatt.com'
        baseurl = '{hyatt}/en/hotel/home.html'.format(hyatt=hyatturl)
        searchurl = '{hyatt}/HICBooking'.format(hyatt=hyatturl)
        unavailable = 'The hotel is not available for your requested travel dates.'
        params = {
            'Lang': 'en',
            'accessibilityCheck': 'false',
            'adults': numppl,
            'childAge1': -1,
            'childAge2': -1,
            'childAge3': -1,
            'childAge4': -1,
            'corp_id': '',
            'day1': start.day,
            'day2': end.day,
            'kids': 0,
            'monthyear1': '{0:%-m} {0:%y}'.format(start),
            'monthyear2': '{0:%-m} {0:%y}'.format(end),
            'offercode': '',
            'pid': 'atlra',
            'rateType': 'Standard',
            'rooms': 1,
            'srcd': 'dayprop',
        }
        try:
            # the requests will redirect a number of times due to how their
            # site processes the search requests
            s = requests.session()
            r = s.get(baseurl, timeout=rtimeout)
            r = s.get(searchurl, params=params, timeout=rtimeout)
            log.debug('[hyatt:rooms] [{0}]'.format(r.status_code))
            results = BeautifulSoup(r.text, 'lxml')
            errors = results.body.select('.error-block #msg .error')
            if errors:
                for err in errors:
                    errtext = [
                        t.strip() for t in err.findAll(text=True, recursive=False)
                        if t.strip() != '']
                    errtext = errtext[0] if len(errtext) > 0 else '<unavailable>'
                    log.debug('ERROR: {0}'.format(errtext))
                log.debug('[hyatt:rooms] UNAVAILABLE')
            else:
                if unavailable in r.text:
                    raise ValueError('invalid detection of availability!')
                log.debug('[hyatt:rooms] AVAILABLE')
        except requests.exceptions.ReadTimeout:
            log.debug('[hyatt:rooms] TIMEOUT')
        return {'stuff': 'things'}

    @timed_function
    def hilton_room_availability(self, log, start, end, numppl=4):
        rtimeout = 10
        baseurl = 'http://www3.hilton.com'
        home = '{0}/en/hotels/georgia/hilton-atlanta-ATLAHHH/index.html'
        home = home.format(baseurl)
        search = '{0}/en_US/hi/search/findhotels/index.htm'.format(baseurl)
        params = {
            'arrivalDate': '{0:%d} {0:%b} {0:%Y}'.format(start),
            'departureDate': '{0:%d} {0:%b} {0:%Y}'.format(end),
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
            'numberOfAdults[0]': numppl,
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
        unavailable = 'There are no rooms available for - at Hilton Atlanta'
        try:
            # the post will redirect a number of times due to how their
            # site processes the search requests
            s = requests.session()
            r = s.get(home, timeout=rtimeout)
            r = s.post(search, params=params, timeout=rtimeout)
            log.debug('[hilton:rooms] [{0}]'.format(r.status_code))
            results = BeautifulSoup(r.text, 'lxml')
            alert_selector = 'div#main_content div#main div.alertBox p'
            alertps = results.body.select(alert_selector)
            alerts = []
            for alertp in alertps:
                errtext = alertp.findAll(text=True, recursive=False)
                errtext = [t.strip() for t in errtext if t.strip() != '']
                alerts.append(' '.join(errtext))
            for error in alerts:
                ratio = fuzz.ratio(error, unavailable)
                log.debug('[hilton:rooms] [{0}] {1}'.format(ratio, error))
                if ratio > 75:
                    # there is an error
                    pass
        except requests.exceptions.ReadTimeout:
            log.debug('[hilton:rooms] TIMEOUT')
        return {'stuff': 'things'}

    @timed_function
    def mariott_room_availability(self, log, start, end, numppl=4):
        rtimeout = 5
        base = 'https://www.marriott.com'
        home = '{0}/hotels/travel/atlmq-atlanta-marriott-marquis/'.format(base)
        search = '{0}/reservation/availabilitySearch.mi'.format(base)
        params = {
            'fromDate': '{0:%m}/{0:%d}/{0:%Y}'.format(start),
            'toDate': '{0:%m}/{0:%d}/{0:%Y}'.format(end),
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
            'numberOfGuests': numppl,
            'numberOfNights': 1,
            'numberOfRooms': 1,
            'propertyCode': 'atlmq',
            'useRewardsPoints': 'false',
        }
        unavailable = 'Sorry, currently there are no rooms available at this '
        unavailable += 'property for the dates you selected. '
        unavailable += 'Please try your search again'
        try:
            s = requests.session()
            r = s.get(home, timeout=rtimeout)
            r = s.get(search, params=params, timeout=rtimeout)
            results = BeautifulSoup(r.text, 'lxml')
            noselector = '#popover-panel #no-rooms-available'
            norooms = results.body.select(noselector)
            if norooms:
                norooms = norooms[0]
            log.debug(norooms.get_text().strip())
            #log.debug((unavailable in r.text))
        except requests.exceptions.ReadTimeout:
            log.debug('[mariott:rooms] TIMEOUT')
        return {'stuff': 'things'}
