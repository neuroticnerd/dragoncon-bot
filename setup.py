#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from __future__ import division, print_function

import io
import re

from setuptools import find_packages, setup


PROJECT_MODULE = 'dragonite'
PROJECT = 'dragonite'
AUTHOR = 'Bryce Eggleton'
EMAIL = 'eggleton.bryce@gmail.com'
DESC = 'Python utilities and tools'
URL = "https://github.com/neuroticnerd/dragoncon-bot"
REQUIRES = []
DEPENDSON = [
    'https://github.com/neuroticnerd/armory/tarball/master#egg=armory-0.1.1',
]
EXTRAS = {
    'dev': (
        'flake8>=2.5.0',
        'pytest>=2.8.4',
        'coverage>=4.0.3',
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
ver_find = r'^\s*__version__\s*=\s*[\"\'](.*)[\"\']'
with io.open(version_file, 'r', encoding='utf-8') as ver_file:
    VERSION = re.search(ver_find, ver_file.read(), re.MULTILINE).group(1)

with io.open('README.md', 'r', encoding='utf-8') as f:
    LONG_DESC = f.read()

with io.open('LICENSE', 'r', encoding='utf-8') as f:
    LICENSE = f.read()

with io.open('reqs', 'r') as reqs_file:
    for rawline in reqs_file:
        line = rawline.strip()
        if line.startswith('-e git://'):
            base = line.split('://')[-1]
            egg = base.split('#')[-1]
            url = base.split('.git#')[0]
            repo = url.split('/')[-1]
            dependency = 'https://{url}/tarball/master#{egg}'.format(
                url=url,
                egg=egg,
            )
            DEPENDSON.append(dependency)
        else:
            REQUIRES.append(line)

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
    dependency_links=DEPENDSON,
    entry_points=SCRIPTS,
    extras_require=EXTRAS,
)
