#!/usr/bin/env python
from setuptools import setup, find_packages

dependency_links = [
    'http://github.com/pbs/django-cms/tarball/support/2.3.x#egg=django-cms-2.3.5pbs.9',
]

setup(
    name='django-cms-roles',
    version='0.4.1',
    description=('Wrapper over django-cms\' permissions that allows '
                 'for easy user management by defining roles that '
                 'span multiple sites.'),
    author='Ioan Alexandru Cucu',
    author_email='alexandruioan.cucu@gmail.com',
    url='https://github.com/kux/django-cms-roles',
    dependency_links=dependency_links,
    install_requires=(
        'parse',
        'Django>=1.3,<1.5',
        'django-cms>=2.3.5,<2.3.6'),
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
