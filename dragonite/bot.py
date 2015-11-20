#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import gevent.monkey
import gevent
import requests

from .hotels import ConHostHotels
from .dragoncon import DragonCon
from .conf import settings


class DragoniteBot(object):
    def __init__(self):
        self._log = settings.get_logger(__name__)
        self.dragoncon = DragonCon()

    def run(self):
        log = self._log
        try:
            dcstr = '{0}'.format(self.dragoncon)
            log.info(dcstr)
        except KeyboardInterrupt:
            pass
        except requests.exceptions.ConnectionError as e:
            log.debug('{0}'.format(e))
            log.error('connection error! now aborting!')
        log.info('dragoncon bot exiting\n')

    def monitor_room_availability(self):
        log = self._log
        for w in settings._warnings:
            log.info(w)
        gevent.monkey.patch_all()
        log.info('gevent monkey patching done')
        tasks = []
        try:
            host_hotels = ConHostHotels(
                self.dragoncon.start,
                self.dragoncon.end
            )
            log.debug('spawning host hotel runner')
            tasks.append(gevent.spawn(host_hotels))
            log.debug('waiting for tasks to complete')
            gevent.wait(tasks)
        except KeyboardInterrupt:
            gevent.killall(tasks)
        except requests.exceptions.ConnectionError as e:
            log.debug('{0}'.format(e))
            log.error('connection error! now aborting!')
            gevent.killall(tasks)
        log.info('dragoncon bot exiting\n')

    def get_room_availability(self):
        log = self._log
        log.debug('runonce check not implemented')
