#! /usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from pip.req import parse_requirements


install_requirements = parse_requirements('requirements.txt')
requirements = [str(ir.req) for ir in install_requirements]


setup(
    name='python-mibody',
    version='0.1',
    description=(
        'Open source Python package for reading data from Salter MiBody '
        'scales'),
    author='Daniel Ward',
    author_email='d@d-w.me',
    packages=['mibody'],
    url='https://github.com/danielward/python-mibody',
    install_requires=requirements,
    test_suite='tests',
)
