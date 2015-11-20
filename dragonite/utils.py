#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import timeit

from decimal import Decimal
from functools import wraps


def timed_function(func):
    @wraps(func)
    def timed_function_wrapper(*args, **kwargs):
        ts = timeit.default_timer()
        result = func(*args, **kwargs)
        te = timeit.default_timer()
        diff = round(Decimal(te - ts), 4)
        return {'time': diff, 'result': result}

    return timed_function_wrapper
