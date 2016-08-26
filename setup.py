#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import io
import os
import re

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))


PROJECT_MODULE = 'dragonite'
PROJECT = 'dragonite'
AUTHOR = 'Bryce Eggleton'
EMAIL = 'eggleton.bryce@gmail.com'
DESC = 'Dragon Con command line utility'
LONG_DESC = ''
KEYWORDS = ('dragonite', 'dragoncon', 'dragon', 'con')
URL = "https://github.com/neuroticnerd/dragoncon-bot"
REQUIRES = []
EXTRAS = {
    'dev': (
        'flake8 >= 2.5.0',
        'twine >= 1.8.1',
        'pytest >= 2.8.4',
        'coverage >= 4.0.3',
    ),
    # 'caching': (
    #     'redis>=2.10.3',
    #     'hiredis>=0.2.0',
    # ),
}
SCRIPTS = {
    "console_scripts": [
        'dragonite = dragonite.cli:dragonite',
    ]}
LICENSE = 'Apache License, Version 2.0'
VERSION = ''
CLASSIFIERS = [
    'Environment :: Console',
    'License :: OSI Approved :: Apache Software License',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
    'Topic :: Utilities',
]

version_file = os.path.join(here, '{0}/__init__.py'.format(PROJECT_MODULE))
ver_find = r'^\s*__version__\s*=\s*[\"\'](.*)[\"\']$'
with io.open(version_file, 'r', encoding='utf-8') as ver_file:
    VERSION = re.search(ver_find, ver_file.read(), re.MULTILINE).group(1)

readme_file = os.path.join(here, 'README.rst')
with io.open(readme_file, 'r', encoding='utf-8') as f:
    LONG_DESC = f.read()

requirements_file = os.path.join(here, 'requirements.txt')
with io.open(requirements_file, 'r') as reqs_file:
    for rawline in reqs_file:
        line = rawline.strip()
        if line.startswith('http'):
            continue
        REQUIRES.append(' >= '.join(line.split('==')))

if __name__ == '__main__':
    setup(
        name=PROJECT,
        version=VERSION,
        packages=find_packages(include=[PROJECT_MODULE + '*']),
        author=AUTHOR,
        author_email=EMAIL,
        url=URL,
        description=DESC,
        long_description=LONG_DESC,
        classifiers=CLASSIFIERS,
        platforms=('any',),
        license=LICENSE,
        keywords=KEYWORDS,
        install_requires=REQUIRES,
        extras_require=EXTRAS,
        entry_points=SCRIPTS,
    )
