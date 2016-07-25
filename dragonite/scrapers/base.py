# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from ..conf import settings


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


class HostHotelScraper(object):
    msgfmt = '{name}:rooms  {msg}'

    def __init__(self, start, end, numppl=4, numrooms=1):
        self.log = settings.get_logger(__name__)
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
