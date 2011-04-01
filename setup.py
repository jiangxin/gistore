#!/usr/bin/env python

from distutils.core import setup

version_string = "0.3.2"

setup(name='gistore',
    version=version_string,
    description='Backup system using DVCS backend, such as git',
    author='Jiang Xin',
    author_email='jiangxin@ossxp.com',
    url='http://open.ossxp.com/',
    package_dir = {'': 'lib'},
    packages=['gistore','gistore.scm'],
    scripts = ['gistore'],
    data_files = [('share/doc/gistore', ['CHANGELOG', 'COPYING', 'README']), ]
    )

# vim: et sw=4 ts=4
