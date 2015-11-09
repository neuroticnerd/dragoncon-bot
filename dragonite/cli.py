#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import click

from .bot import DragonConBot, DragoniteConfig


@click.command()
@click.option(
    '-l', '--loglevel', 'loglevel',
    type=click.Choice(['debug', 'info', 'warn', 'error']))
@click.version_option(message='%(prog)s %(version)s')
@click.pass_context
def dragonite(ctx, loglevel):
    # command parameters override environment config
    config = DragoniteConfig(loglevel=loglevel)

    # run the dragonite bot
    draconcon_bot = DragonConBot(config)
    draconcon_bot.run()


if __name__ == '__main__':
    dragonite()
