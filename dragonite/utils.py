#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import logging
import timeit

from decimal import Decimal
from functools import wraps


def get_stream_logger(logname, loglevel=logging.INFO):
    # https://gist.github.com/neuroticnerd/7c60d61c8d9d9716f50d
    logger = logging.getLogger(logname)
    logger.propagate = False
    logger.setLevel(loglevel)
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def timed_function(func):
    @wraps(func)
    def timed_function_wrapper(*args, **kwargs):
        ts = timeit.default_timer()
        result = func(*args, **kwargs)
        te = timeit.default_timer()
        diff = round(Decimal(te - ts), 4)
        return {'time': diff, 'result': result}

    return timed_function_wrapper
