#!/usr/bin/env python
from setuptools import setup, find_packages

dependency_links = [
    'http://github.com/pbs/django-cms/tarball/support/2.3.x#egg=django-cms-2.3.5pbs.X.dev',
    'http://github.com/pbs/django-admin-extend/tarball/master#egg=django-admin-extend-dev',
]

dependencies = [
    'Django>=1.8,<1.9',
    'django-cms>=2.3.5,<2.3.6',
    'django-admin-extend',
]

setup(
    name='django-cms-roles',
    version='0.7.0.pbs.7',
    description=('Wrapper over django-cms\' permissions that allows '
                 'for easy user management by defining roles that '
                 'span multiple sites.'),
    author='Ioan Alexandru Cucu',
    author_email='alexandruioan.cucu@gmail.com',
    url='https://github.com/kux/django-cms-roles',
    dependency_links=dependency_links,
    install_requires=dependencies,
    packages=find_packages(),
    include_package_data=True,
)
