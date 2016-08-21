# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from .hilton import HiltonAvailability
from .hyatt import HyattAvailability
from .hyattpasskey import HyattPasskeyAvailability
from .marriott import MarriottAvailability
from .marriott_discount import MarriottDiscountAvailability


def get_scrapers(start, end):
    """ should this be done in the coroutines? """
    return (
        HyattAvailability(start, end),
        HyattPasskeyAvailability(start, end),
        HiltonAvailability(start, end),
        MarriottAvailability(start, end),
        MarriottDiscountAvailability(start, end),
    )


def get_host_names():
    return (
        HiltonAvailability.name,
        HyattAvailability.name,
        HyattPasskeyAvailability.name,
        MarriottAvailability.name,
        MarriottDiscountAvailability.name,
    )
