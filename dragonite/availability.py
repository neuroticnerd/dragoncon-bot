# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import requests

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

from .utils import timed_function, AvailabilityResults, SearchResponse


class HostHotelAvailability(object):
    def __init__(self, start, end, numppl=4):
        self.start = start
        self.end = end
        self.numppl = numppl

    def __call__(self, method, *args, **kwargs):
        return getattr(self, method)(*args, **kwargs)

    def scrape(self):
        raise NotImplementedError('must implement scrape method')

    def parse(self):
        raise NotImplementedError('must implement parse method')


class HyattAvailability(HostHotelAvailability):
    @timed_function
    def scrape(self):
        # a large timeout is required because their redirects take a very
        # long time to process and actually return a response
        rtimeout = 8
        availability = AvailabilityResults()
        hyatturl = 'https://atlantaregency.hyatt.com'
        baseurl = '{hyatt}/en/hotel/home.html'.format(hyatt=hyatturl)
        searchurl = '{hyatt}/HICBooking'.format(hyatt=hyatturl)
        unavailable = (
            'The hotel is not available for'
            ' your requested travel dates.')
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
            # the requests will redirect a number of times due to how their
            # site processes the search requests
            s = requests.session()
            r = s.get(baseurl, timeout=rtimeout)
            r = s.get(searchurl, params=params, timeout=rtimeout)
            self.log.debug('[hyatt:rooms] [{0}]'.format(r.status_code))
            results = BeautifulSoup(r.text, 'lxml')
            self.log.error('{0}'.format(
                'No lodging matches your search criteria.' in r.text
            ).upper())
            errors = results.body.select('.error-block #msg .error')
            if errors:
                for err in errors:
                    errtext = [
                        t.strip() for t in err.findAll(
                            text=True, recursive=False)
                        if t.strip() != '']
                    nothere = '<unavailable>'
                    errtext = errtext[0] if len(errtext) > 0 else nothere
                    self.log.debug('ERROR: {0}'.format(errtext))
                self.log.info('[hyatt:rooms] UNAVAILABLE')
            else:
                if unavailable in r.text:
                    raise ValueError('invalid detection of availability!')
                self.log.info('[hyatt:rooms] AVAILABLE')
        except requests.exceptions.ReadTimeout:
            availability.errors.append('TIMEOUT')
            self.log.error('[hyatt:rooms] TIMEOUT')
            return availability
        except requests.exceptions.ConnectionError:
            availability.errors.append('CONNECTION ERROR')
            self.log.error('[hyatt:rooms] CONNECTION ERROR')
            return availability
        availability.status = 'success'
        return availability


class HyattPasskeyAvailability(HostHotelAvailability):
    @timed_function
    def scrape(self):
        """
        TODO: hyatt now uses:
            https://aws.passkey.com/event/14179207/owner/323/rooms/list
        """
        availability = AvailabilityResults()
        rtimeout = 8
        datefmt = '{0:%Y}-{0:%m}-{0:%d}'
        start = datefmt.format(self.start)
        end = datefmt.format(self.end)
        hyatturl = 'https://aws.passkey.com/event/14179207/owner/323'
        baseurl = '{0}/home'.format(hyatturl)
        landingurl = '{0}/landing'.format(hyatturl)
        searchurl = '{0}/rooms/select'.format(hyatturl)
        payload = {
            'hotelId': 0,
            'blockMap.blocks{0}5B0{0}5D.blockId'.format('%'): 0,
            'blockMap.blocks{0}5B0{0}5D.checkIn'.format('%'): start,
            'blockMap.blocks{0}5B0{0}5D.checkOut'.format('%'): end,
            'blockMap.blocks{0}5B0{0}5D.numberOfGuests'.format('%'): 4,
            'blockMap.blocks{0}5B0{0}5D.numberOfRooms'.format('%'): 1,
            'blockMap.blocks{0}5B0{0}5D.numberOfChildren'.format('%'): 0,
        }
        unavailable = 'No lodging matches your search criteria.'

        try:
            s = requests.session()
            r = s.get(baseurl, timeout=rtimeout)
            r = s.get(landingurl, timeout=rtimeout)
            r = s.post(searchurl, data=payload, timeout=rtimeout)

            self.log.debug('[hyatt:rooms] [{0}]'.format(r.status_code))
            results = BeautifulSoup(r.text, 'lxml')
            self.log.error('{0}'.format(
                unavailable in r.text
            ).upper())
            errors = results.body.select('.error-block #msg .error')
            if errors:
                for err in errors:
                    errtext = [
                        t.strip() for t in err.findAll(
                            text=True, recursive=False)
                        if t.strip() != '']
                    nothere = '<unavailable>'
                    errtext = errtext[0] if len(errtext) > 0 else nothere
                    self.log.debug('ERROR: {0}'.format(errtext))
                self.log.info('[hyatt:rooms] UNAVAILABLE')
            else:
                if unavailable in r.text:
                    raise ValueError('invalid detection of availability!')
                self.log.info('[hyatt:rooms] AVAILABLE')
        except requests.exceptions.ReadTimeout:
            availability.errors.append('TIMEOUT')
            self.log.error('[hyatt:rooms] TIMEOUT')
            return availability
        except requests.exceptions.ConnectionError:
            availability.errors.append('CONNECTION ERROR')
            self.log.error('[hyatt:rooms] CONNECTION ERROR')
            return availability
        availability.status = 'success'
        return availability


class HiltonAvailability(HostHotelAvailability):
    @timed_function
    def scrape(self):
        rtimeout = 10
        availability = AvailabilityResults()
        baseurl = 'http://www3.hilton.com'
        home = '{0}/en/hotels/georgia/hilton-atlanta-ATLAHHH/index.html'
        home = home.format(baseurl)
        search = '{0}/en_US/hi/search/findhotels/index.htm'.format(baseurl)
        params = {
            'arrivalDate': '{0:%d} {0:%b} {0:%Y}'.format(self.start),
            'departureDate': '{0:%d} {0:%b} {0:%Y}'.format(self.end),
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
        unavailable = 'There are no rooms available for - at Hilton Atlanta'
        try:
            # the post will redirect a number of times due to how their
            # site processes the search requests
            s = requests.session()
            r = s.get(home, timeout=rtimeout)
            r = s.post(search, params=params, timeout=rtimeout)
            self.log.debug('[hilton:rooms] [{0}]'.format(r.status_code))
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
                self.log.debug('[hilton:rooms] [{0}] {1}'.format(ratio, error))
                if ratio > 75:
                    self.log.info(error)
        except requests.exceptions.ReadTimeout:
            availability.errors.append('TIMEOUT')
            self.log.error('[hilton:rooms] TIMEOUT')
            return availability
        except requests.exceptions.ConnectionError:
            availability.errors.append('CONNECTION ERROR')
            self.log.error('[hilton:rooms] CONNECTION ERROR')
            return availability
        availability.status = 'success'
        return availability


class MariottAvailability(HostHotelAvailability):
    @timed_function
    def scrape(self):
        rtimeout = 5
        availability = AvailabilityResults()
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
                norooms = norooms[0].get_text().strip()
                self.log.info(norooms)
                if unavailable not in norooms:
                    errmsg = 'norooms present but unavailable not found'
                    raise ValueError(errmsg)
        except requests.exceptions.ReadTimeout:
            availability.errors.append('TIMEOUT')
            self.log.error('[mariott:rooms] TIMEOUT')
            return availability
        except requests.exceptions.ConnectionError:
            availability.errors.append('CONNECTION ERROR')
            self.log.error('[mariott:rooms] CONNECTION ERROR')
            return availability
        availability.status = 'success'
        return availability
