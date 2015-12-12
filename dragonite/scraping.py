# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import requests

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

from .utils import timed_function, AvailabilityResults


@timed_function
def hyatt_room_availability(log, start, end, numppl=4):
    """
    TODO: hyatt now uses:
        https://aws.passkey.com/event/14179207/owner/323/rooms/list
    """
    availability = AvailabilityResults()
    rtimeout = 8
    datefmt = '{0:%Y}-{0:%m}-{0:%d}'
    start = datefmt.format(start)
    end = datefmt.format(end)
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

        log.debug('[hyatt:rooms] [{0}]'.format(r.status_code))
        results = BeautifulSoup(r.text, 'lxml')
        log.error('{0}'.format(
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
                log.debug('ERROR: {0}'.format(errtext))
            log.info('[hyatt:rooms] UNAVAILABLE')
        else:
            if unavailable in r.text:
                raise ValueError('invalid detection of availability!')
            log.info('[hyatt:rooms] AVAILABLE')
    except requests.exceptions.ReadTimeout:
        availability.errors.append('TIMEOUT')
        log.error('[hyatt:rooms] TIMEOUT')
        return availability
    except requests.exceptions.ConnectionError:
        availability.errors.append('CONNECTION ERROR')
        log.error('[hyatt:rooms] CONNECTION ERROR')
        return availability
    availability.status = 'success'
    return availability


@timed_function
def hilton_room_availability(log, start, end, numppl=4):
    rtimeout = 10
    availability = AvailabilityResults()
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
                log.info(error)
    except requests.exceptions.ReadTimeout:
        availability.errors.append('TIMEOUT')
        log.error('[hilton:rooms] TIMEOUT')
        return availability
    except requests.exceptions.ConnectionError:
        availability.errors.append('CONNECTION ERROR')
        log.error('[hilton:rooms] CONNECTION ERROR')
        return availability
    availability.status = 'success'
    return availability


@timed_function
def mariott_room_availability(log, start, end, numppl=4):
    rtimeout = 5
    availability = AvailabilityResults()
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
            norooms = norooms[0].get_text().strip()
            log.info(norooms)
            if unavailable not in norooms:
                errmsg = 'norooms present but unavailable not found'
                raise ValueError(errmsg)
    except requests.exceptions.ReadTimeout:
        availability.errors.append('TIMEOUT')
        log.error('[mariott:rooms] TIMEOUT')
        return availability
    except requests.exceptions.ConnectionError:
        availability.errors.append('CONNECTION ERROR')
        log.error('[mariott:rooms] CONNECTION ERROR')
        return availability
    availability.status = 'success'
    return availability
