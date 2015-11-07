#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import click

from .bot import DragonConBot


@click.command()
@click.option(
    '--verbose', 'verbose',
    flag_value=True, help='enable verbose logging')
def dragonite(verbose=False):
    dcbot = DragonConBot()
    dcbot.run()


if __name__ == '__main__':
    dragonite()
