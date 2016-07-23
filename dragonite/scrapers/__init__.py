# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from .hilton import HiltonAvailability
from .hyatt import HyattAvailability
from .hyattpasskey import HyattPasskeyAvailability
from .mariott import MariottAvailability


def get_scrapers(start, end):
    """ should this be done in the coroutines? """
    return (
        HyattAvailability(start, end),
        HyattPasskeyAvailability(start, end),
        HiltonAvailability(start, end),
        MariottAvailability(start, end),
    )
