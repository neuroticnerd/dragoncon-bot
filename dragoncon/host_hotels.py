#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import gevent.queue


def room_availability(log, host_hotels, q):
    queue = q
    while True:
        try:
            hotel = queue.get(timeout=0)
            if not host_hotels[hotel]:
                break
            log.info('getting {0} availability'.format(hotel))
            gevent.sleep(1)
            queue.put(hotel)
        except gevent.queue.Empty:
            break
