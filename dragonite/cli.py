#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import click

from .dragoncon import DragonCon
from .conf import settings
from .constants import DRAGONITE_ASCII


@click.group(invoke_without_command=True)
@click.option(
    '-c', '--cache', 'cache',
    is_flag=True, default=False,
    help=(
        'Accepts "[Tt]rue", "[Ff]alse", "yes", "no", '
        'and 0/1 to enable/disable caching.'
    )
)
@click.option(
    '-d', '--debug', 'debug',
    is_flag=True, default=False,
    help='Puts Dragonite into debug mode.'
)
@click.option(
    '-l', '--loglevel', 'loglevel',
    type=click.Choice(['debug', 'info', 'warn', 'error']),
    default='info',
    help='Sets the lowest level of log messages to show; defaults to "info"'
)
@click.option(
    '-m', '--max-tries', 'max_attempts',
    type=int,
    help='Set the max number of tries to find room availability.'
)
@click.option(
    '-v', '--verbose', 'verbose',
    is_flag=True, default=False,
    help='Causes log messages to include date, time, and module information.'
)
@click.version_option(message='%(prog)s %(version)s')
@click.pass_context
def dragonite(context, cache, debug, loglevel, max_attempts, verbose):
    # CLI options/args override defaults and env vars
    settings.use_cache = cache
    settings.debug = debug
    settings.loglevel = loglevel
    if max_attempts is not None:
        settings.max_attempts = max_attempts
    settings.verbose = verbose
    dragoncon_bot = DragonCon()
    context.obj = dragoncon_bot
    log = settings.get_logger(__name__)
    log.debug(settings)
    log.debug('subcommand=\'{0}\''.format(context.invoked_subcommand))
    log.info(DRAGONITE_ASCII)
    if context.invoked_subcommand is None:
        dragoncon_bot.run()


@click.command()
@click.option(
    '-m', '--max-tries', 'max_attempts',
    type=int, default=1,
    help='Set the max number of tries to find room availability.'
)
@click.pass_context
def rooms(context, max_attempts):
    log = settings.get_logger(__name__)
    if max_attempts != 1:
        log.warning('max attempts is not 1! ({0})'.format(max_attempts))
    settings.max_attempts = max_attempts
    log.debug('running "rooms" subcommand')
    context.obj.run()


@click.command()
@click.pass_context
def test(context):
    def get_cookies_dict():
        return {'test-cookie': 'some stupid value'}
    from dragonite.scrapers.base import ScrapeResults
    log = settings.get_logger(__name__)
    settings.debug = True
    with settings.comm as gateway:
        log.debug(gateway._gateway._server)
        log.debug(gateway._gateway._smtp_user)
        log.debug(gateway._gateway._passcode)
        test_data = ScrapeResults(None)
        test_data._raw = 'This is test raw_response data!'
        test_data._session = ScrapeResults(None)
        test_data._session.cookies = ScrapeResults(None)
        test_data._session.cookies.get_dict = get_cookies_dict
        test_data._parent = ScrapeResults(None)
        test_data._parent.friendly = 'TEST HOTEL NAME'
        test_data._parent.phone = '555-555-5555'
        test_data._parent.link = 'http://lmgtfy.com/?q=dragon+con'
        gateway.notify(test_data)


dragonite.add_command(rooms)
dragonite.add_command(test)


if __name__ == '__main__':
    dragonite()
