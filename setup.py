#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import re
from setuptools import setup, find_packages


def fread(filename, split=False, keepnl=False):
    """May raise IOError exceptions from file operations"""
    result = ""
    if split:
        result = []
    with open(filename, 'r') as f:
        # use readme.read().decode("utf-8") instead?
        for line in f:
            tmpline = line
            if line == '\n':
                continue
            if split:
                if '#' in tmpline.strip()[:2]:
                    continue
                result.append(line.replace('\n', ''))
            else:
                result += line
    return result


PROJECT_MODULE = 'dragonite'
PROJECT = 'dragoncon-bot'
AUTHOR = 'Bryce Eggleton'
EMAIL = 'eggleton.bryce@gmail.com'
DESC = 'Python utilities and tools'
LONG_DESC = fread('README.md')
LICENSE = fread('LICENSE')
URL = "https://github.com/neuroticnerd/dragoncon-bot"
REQUIRES = fread('reqs', True)
SCRIPTS = {
    "console_scripts": [
        'dragonite = dragonite.__main__:main',
    ]}

with open('{0}/__init__.py'.format(PROJECT_MODULE), 'r') as modinit:
    findver = re.compile(r'^\s*__version__\s*=\s*[\"\'](.*)[\"\']', re.M)
    try:
        VERSION = findver.search(modinit.read()).group(1)
    except AttributeError:
        VERSION = '0.1.0'

setup(
    name=PROJECT,
    version=VERSION,
    packages=find_packages(include=[PROJECT_MODULE]),
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    description=DESC,
    long_description=LONG_DESC,
    license=LICENSE,
    install_requires=REQUIRES,
    entry_points=SCRIPTS,
)
