#!/usr/bin/env python

from distutils.core import setup
from subprocess import Popen, PIPE, STDOUT

proc_desc  = Popen( [ "git", "describe", "--always", "--dirty" ], stdout=PIPE )
version = proc_desc.communicate()[0]
if version.startswith("v"):
    version = version[1:]

setup(name='gistore',
    version=version,
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
