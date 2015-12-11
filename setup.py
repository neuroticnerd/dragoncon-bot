#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import re

from setuptools import setup, find_packages
from io import open


PROJECT_MODULE = 'dragonite'
PROJECT = 'dragonite'
AUTHOR = 'Bryce Eggleton'
EMAIL = 'eggleton.bryce@gmail.com'
DESC = 'Python utilities and tools'
URL = "https://github.com/neuroticnerd/dragoncon-bot"
REQUIRES = [
    'click>=5.1',
    'gevent>=1.1b6',
    'lxml>=3.4.4',
    'python-dateutil>=2.4.2',
    'armory>=0.1.0',
    'requests>=2.8.1',
    'beautifulsoup4>=4.4.1',
    'python-Levenshtein>=0.12.0',
    'fuzzywuzzy>=0.7.0',
    'Unidecode>=0.4.18',
]
EXTRAS = {
    'dev': (
        'flake8>=2.5.0',
        'pytest>=2.8.4',
        'coverage>=4.0.3',
    ),
    'caching': (
        'redis>=2.10.3',
        'hiredis>=0.2.0',
    ),
}
SCRIPTS = {
    "console_scripts": [
        'dragonite = dragonite.cli:dragonite',
    ]}
LONG_DESC = ''
LICENSE = ''
VERSION = ''
CLASSIFIERS = [
    'Environment :: Console',
    'Topic :: Utilities',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.5',
]

version_file = '{0}/__init__.py'.format(PROJECT_MODULE)
with open(version_file, 'r', encoding='utf-8') as fver:
    re_ver = r'^\s*__version__\s*=\s*[\"\'](.*)[\"\']$'
    VERSION = re.search(re_ver, fver.read(), re.MULTILINE).group(1)

with open('README.md', 'r', encoding='utf-8') as f:
    LONG_DESC = f.read()

with open('LICENSE', 'r', encoding='utf-8') as f:
    LICENSE = f.read()

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
    extras_require=EXTRAS,
)
