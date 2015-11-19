#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import click

from .bot import DragoniteBot, DragoniteConfig


@click.group(invoke_without_command=True)
@click.option(
    '-l', '--loglevel', 'loglevel',
    type=click.Choice(['debug', 'info', 'warn', 'error']),
    default='info',
    help='Sets the lowest level of log messages to show; defaults to "info"'
)
@click.option(
    '-c', '--cache', 'cache',
    is_flag=True, default=True,
    help=(
        'Accepts "[Tt]rue", "[Ff]alse", "yes", "no", '
        'and 0/1 to enable/disable caching.'
    )
)
@click.option(
    '-v', '--verbose', 'verbose',
    is_flag=True, default=False,
    help='Causes log messages to include date, time, and module information.'
)
@click.version_option(message='%(prog)s %(version)s')
@click.pass_context
def dragonite(context, loglevel, cache, verbose):
    config = DragoniteConfig(loglevel=loglevel, cache=cache, verbose=verbose)
    dragoncon_bot = DragoniteBot(config)
    context.obj = dragoncon_bot
    log = config.get_logger(__name__)
    log.debug(config)
    log.debug('subcommand=\'{0}\''.format(context.invoked_subcommand))
    if context.invoked_subcommand is None:
        dragoncon_bot.run()


@click.command()
@click.option(
    '-m', '--monitor', 'monitor',
    is_flag=True, default=False,
    help='Causes the room availability to only be checked once.'
)
@click.pass_context
def rooms(context, monitor):
    if monitor:
        context.obj.monitor_room_availability()
    else:
        context.obj.get_room_availability()

dragonite.add_command(rooms)


if __name__ == '__main__':
    dragonite()
