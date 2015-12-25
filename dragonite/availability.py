# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import requests

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

from .conf import settings


def get_scrapers(start, end):
    """ should this be done in the coroutines? """
    return (
        HyattAvailability(start, end),
        HyattPasskeyAvailability(start, end),
        HiltonAvailability(start, end),
        MariottAvailability(start, end),
    )


class ScrapeResults(object):
    def __init__(self, parent):
        self._parent = parent
        self._raw = None
        self._dom = None
        self._session = None
        self._response = None
        self.available = False
        self.unavailable = False
        self.post_process = False
        self.error = False

    @property
    def parent(self):
        return self._parent

    @property
    def raw(self):
        return self._raw

    @property
    def dom(self):
        return self._dom

    @property
    def session(self):
        return self._session

    @property
    def response(self):
        return self._response

    def evaluate(self):
        self.parent.parse(self)


class HostHotelAvailability(object):
    msgfmt = '{name}:rooms  {msg}'

    def __init__(self, start, end, numppl=4):
        self.log = settings.get_logger(__name__)
        self.start = start
        self.end = end
        self.numppl = numppl

    def __call__(self, *args, **kwargs):
        """ convenience method of triggering a scrape """
        return self.scrape(result=ScrapeResults(self))

    @property
    def name(self):
        raise NotImplementedError('must have name attribute')

    @property
    def friendly(self):
        raise NotImplementedError('must have friendly attribute')

    def scrape(self, result, **kwargs):
        """ expected to return a ScrapeResults object """
        raise NotImplementedError('must implement scrape method')

    def parse(self, result, **kwargs):
        raise NotImplementedError('must implement parse method')

    def msg(self, message):
        return self.msgfmt.format(name=self.name, msg=message)


class HyattAvailability(HostHotelAvailability):
    name = 'hyatt'
    friendly = 'Hyatt'

    def scrape(self, result, *args, **kwargs):
        log = self.log
        # a large timeout is required because their redirects take a very
        # long time to process and actually return a response
        rtimeout = kwargs.get('timeout', 8)
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
        try:
            # the request will redirect a number of times due to
            # how their site processes the search requests
            s = requests.Session()
            result._session = s
            r = result.session.get(baseurl, timeout=rtimeout)
            r = result.session.get(searchurl, params=params, timeout=rtimeout)
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
        search_text = (
            'The hotel is not available for your requested travel dates.'
            ' It is either sold out or not yet open for reservations.'
        )

        errors = result.dom.body.select('.error-block #msg .error')
        for error in errors:
            if result.unavailable is True:
                break
            for text in error.findAll(text=True, recursive=False):
                if search_text in text.strip():
                    result.unavailable = True
                    result.post_process = False
                    log.debug(self.msg('UNAVAILABLE'))
                    break

        if not errors and search_text in result._raw:
            errmsg = 'potential invalid detection of availability!'
            log.error(self.msg(errmsg))
            raise ValueError(errmsg)

        if not result.unavailable:
            result.post_process = True
            log.debug(self.msg('post processing required'))

        return self


class HyattPasskeyAvailability(HostHotelAvailability):
    name = 'hyatt_passkey'
    friendly = 'Hyatt (passkey)'

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


class HiltonAvailability(HostHotelAvailability):
    name = 'hilton'
    friendly = 'Hilton'

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


class MariottAvailability(HostHotelAvailability):
    name = 'mariott'
    friendly = 'Mariott'

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
