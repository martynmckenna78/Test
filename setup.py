#! /usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from pip.req import parse_requirements


install_requirements = parse_requirements('requirements.txt', session='')
requirements = [str(ir.req) for ir in install_requirements]


setup(
    name='python-mibody',
    version='0.1.2',
    description=(
        'Lightweight open source Python 3 package for reading data from '
        'Salter MiBody scales'),
    author='Daniel Ward',
    author_email='d@d-w.me',
    packages=['mibody'],
    url='https://github.com/danielward/python-mibody',
    download_url='https://github.com/danielward/python-mibody/tarball/0.1.2',
    install_requires=requirements,
    test_suite='tests',
)
