#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    name='django-cms-roles',
    version='0.4.0',
    description=('Wrapper over django-cms\' permissions that allows '
                 'for easy user management by defining roles that '
                 'span multiple sites.'),
    author='Ioan Alexandru Cucu',
    author_email='alexandruioan.cucu@gmail.com',
    url='https://github.com/kux/django-cms-roles',
    install_requires=(
        'parse',
        'Django>=1.3,<1.5',
        'django-cms>=2.3,<2.4'),
    setup_requires=[
        's3sourceuploader',
    ],
    tests_require=[
        'django-nose',
        'mock==1.0.1',
    ],
    test_suite='runtests.runtests',
    packages=find_packages(),
    include_package_data=True,
)
