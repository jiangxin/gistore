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

import sys
import os
import logging

GISTORE_CONFIG_DIR  = ".gistore"
GISTORE_LOG_DIR     = "logs"
GISTORE_LOCK_DIR    = "locks"

class DefaultConfig(object):
    if os.getuid() != 0:
        sys_config_dir = os.path.expanduser('~/.gistore.d/etc')
        tasks_dir = os.path.expanduser('~/.gistore.d/tasks')
    else:
        sys_config_dir = '/etc/gistore'
        tasks_dir = '/etc/gistore/tasks'
    backend = "git"
    backuphistory = 200

    root_only = False
    log_level = logging.INFO
    task = None
    backuphistory = 200
    backupcopies  = 5
    store_list = {'default': None }

def initConfig():
    for path in ( DefaultConfig.tasks_dir, DefaultConfig.sys_config_dir ):
        if not os.path.exists( path ):
            try:
                os.makedirs( path )
            except OSError:
                print >> sys.stderr, "no permisson to create dir: %s" % path
                return

    config_file = os.path.join(DefaultConfig.sys_config_dir, 'local_config.py')
    if os.path.exists(config_file):
        return

    try:
        fp = open(config_file, "w")
    except IOError:
        print >> sys.stderr, "no permisson to create file: %s" % config_file
    else:
        fp.write("""# -*- coding: utf-8 -*-
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

from gistore.config import DefaultConfig

DEFAULT_BACKUPS = []

##Example: dynamic backup list
#import subprocess
#proc = subprocess.Popen(
#           ['python', '/opt/ossxp/bin/ossxp_pkgadmin.py', 'list_backup'],
#           stdout=subprocess.PIPE, stderr=open('/dev/null', 'w') )
#for line in proc.communicate()[0].splitlines():
#    DEFAULT_BACKUPS.append(line.strip())

class Config(DefaultConfig):
    store_list = {'default': DEFAULT_BACKUPS }

# vim: et ts=4 sw=4
""")
        fp.close()

def getConfig():
    try:
        #Initial sys_config_dir if not exists.
        if not os.path.exists( os.path.join( DefaultConfig.sys_config_dir,
                                             'local_config.py' ) ):
            initConfig()

        # load custom config file in /etc/gistore/local_config.py
        sys.path.insert(0, DefaultConfig.sys_config_dir);
        module = __import__('local_config', globals(), {})
        configClass = getattr(module, 'Config')
        cfg = configClass()
    except ImportError:
        cfg = DefaultConfig()

    return cfg

cfg = getConfig()

# vim: et ts=4 sw=4
