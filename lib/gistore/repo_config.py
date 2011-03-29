# -*- coding: utf-8 -*-
#
# gistore -- Backup files using DVCS, such as git.
# Copyright (C) 2010 Jiang Xin <jiangxin@ossxp.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#

import os
import logging
from subprocess import Popen, PIPE, STDOUT

from gistore.utils import *
from gistore.config import *
from gistore.errors import *
from gistore        import versions

log = logging.getLogger('gist.repo_config')


class RepoConfig(object):

    def __init__(self, filename):
        self.filename = filename
        self.repo_cfg = {
                         "main.backend": cfg.backend,
                         "main.rootonly": os.getuid() == 0 and 'true' or
                                          ( cfg.root_only and
                                            'true' or 'false'),
                         "main.backuphistory": str(cfg.backuphistory),
                         "main.backupcopies": str(cfg.backupcopies),
                         "main.version": str(versions.GISTORE_VERSION),
                         'default.keepemptydir': 'false',
                         'default.keepperm': 'false',
                        }
        self.defaults = {}

        if os.path.exists(self.filename):
            self._load()

 
    def _load(self):
        command = [ 'git', 'config', '-f', self.filename, '-l' ]
        proc = Popen( command, stdout=PIPE, stderr=None)
        try:
            stdout = communicate( proc, command, verbose=False )[0]
        except:
            self._convert()
            proc = Popen( command, stdout=PIPE, stderr=None)
            stdout = communicate( proc, command )[0]

        for line in stdout.splitlines():
            key, val = line.split('=', 1)
            self.repo_cfg[ key.strip() ] = val.strip()

        for key in filter( lambda n: n.startswith('default.'),
                           self.repo_cfg.keys() ):
            self.defaults[ key[8:] ] = self.repo_cfg[key]


    def save(self, filename=None):
        for key,val in sorted(self.repo_cfg.items()):
            self.add(key, val, False, filename=filename)


    def add(self, rawkey, val, update=True, filename=None):
        filename = filename or self.filename
        if isinstance( val, bool ):
            val = val and 'true' or 'false'
        elif not isinstance( val, basestring):
            val = str(val)
        m, n = rawkey.strip().rsplit('.', 1)
        key = "%s.%s" % ( m, n.lower() )
        command = [ 'git', 'config', '-f', filename ]
        proc = Popen( command + [ key, val ],
                      stdout=PIPE,
                      stderr=STDOUT )
        communicate( proc, command + [ key, val ] )
        if update:
            self.repo_cfg[key] = val

       
    def set(self, rawkey, val, update=True, filename=None):
        return self.add( rawkey, val, update=update, filename=filename)


    def remove_section(self, section, filename=None):
        filename = filename or self.filename
        section = section.strip()
        command = [ 'git', 'config', '-f', filename,
                    '--remove-section', section ]
        proc = Popen( command, stdout=PIPE, stderr=PIPE )
        communicate( proc, command,
                     ignore=lambda n: n=='fatal: No such section!',
                     exception=False )

        remove_keys = []
        for key in self.repo_cfg.iterkeys():
            if key.startswith("%s." % section):
                remove_keys.append(key)
        for key in remove_keys:
            del(self.repo_cfg[key])


    def remove(self, rawkey, filename=None):
        filename = filename or self.filename
        m, n = rawkey.strip().rsplit('.', 1)
        key = "%s.%s" % ( m, n.lower() )
        command = [ 'git', 'config', '-f', filename,
                    '--unset-all', key ]
        proc = Popen( command, stdout=PIPE, stderr=PIPE )
        communicate( proc, command, exception=False )
        if self.repo_cfg.has_key(key):
            del(self.repo_cfg[key])


    def _convert(self):
        from ConfigParser import ConfigParser
        cp=ConfigParser()
        cp.read(self.filename)
        for section in [ 'main', 'default' ]:
            if cp.has_section( section ):
                for key, val in cp.items(section):
                    key = key.lower().replace('_', '')
                    self.repo_cfg[ "%s.%s" % (section, key) ] = val

        for section in filter( lambda n: n.startswith('store '),
                               cp.sections() ):
            for key, val in cp.items(section):
                key = key.lower().replace('_', '')
                self.repo_cfg[ "store.%s.%s" % (section[6:].strip(' "'), key) ] = val
            if not self.repo_cfg.has_key( "store.%s.enabled" % section[6:].strip(' "') ):
                self.repo_cfg[ "store.%s.enabled" % section[6:].strip(' "') ] = "true"

        tmpfile = "%s.%d.%s" % ( self.filename, os.getpid(), ".tmp" )
        try:
            self.save( tmpfile )
            os.rename( tmpfile, self.filename )
        except:
            os.unlink( tmpfile )
            raise


# vim: et ts=4 sw=4
