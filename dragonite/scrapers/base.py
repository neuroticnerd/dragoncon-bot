from __future__ import absolute_import, unicode_literals


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

    def evaluate(self):
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
