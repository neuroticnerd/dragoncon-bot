# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import timeit

from decimal import Decimal
from functools import wraps


class AvailabilityResults(object):
    def __init__(self, results=None, elapsed=None):
        self.status = 'failed'
        self.errors = []
        self.results = None
        self.available = False
        self.elapsed = elapsed


def timed_function(func):
    @wraps(func)
    def timed_function_wrapper(*args, **kwargs):
        time_start = timeit.default_timer()
        result = func(*args, **kwargs)
        elapsed = round(Decimal(timeit.default_timer() - time_start), 4)
        if isinstance(result, AvailabilityResults):
            result.elapsed = elapsed
            return result
        return AvailabilityResults(result, elapsed)

    return timed_function_wrapper
