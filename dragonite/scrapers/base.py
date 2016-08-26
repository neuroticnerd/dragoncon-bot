from __future__ import absolute_import, unicode_literals

import logging
import traceback

from requests.exceptions import ConnectionError, ReadTimeout


class RequestsGuard(object):

    def __init__(self, result, logname=None):
        self.log = logging.getLogger((logname if logname else __name__))
        self.result = result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        handled = False

        if exc_value is not None:
            self.result.error = True
            self.result.traceback = ''.join(traceback.format_exception(
                exc_type, exc_value, exc_traceback
            ))

            if issubclass(exc_type, ReadTimeout):
                self.log.error(self.result.parent.msg('TIMEOUT'))
                handled = True
            elif issubclass(exc_type, ConnectionError):
                self.log.error(self.result.parent.msg('CONNECTION ERROR'))
                handled = True

        return handled


class ScrapeResults(object):

    def __init__(self, parent):
        self.parent = parent
        self.raw = None
        self.dom = None
        self.session = None
        self.response = None
        self.available = False
        self.post_process = False
        self.error = False
        self.traceback = None

    def evaluate(self):
        if self.error is False:
            self.parent.parse(self)


class HostHotelScraper(object):
    msgfmt = '{name}:rooms  {msg}'

    def __init__(self, start, end, numppl=4, numrooms=1):
        self.start = start
        self.end = end
        self.numppl = numppl
        self.numrooms = numrooms

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
