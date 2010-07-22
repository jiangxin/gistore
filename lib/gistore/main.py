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

'''PROGRAM INTRODUCTION
Gistore is a backup system with a DVCS as backend, and git is highly
recommended. Orignally or currently only git is supportted. So, you
must have git installed. For git installation, see http://git-scm.com/.

Gistore can *store* files and directories from any place, without copying
or sync files to the gistore DVCS working tree. All the backup files
and directories are mounted to the gistore DVCS working tree on the fly.

Usage: %(PROGRAM)s [options]

Options:

    -h|--help
        Print this message and exit.
    -v|--verbose
        Verbose mode: more debug message
    -q|--quiet
        Quiet mode: less message
    -r <taskname> | -r <repos_dir>
        Set taskname or repos directory

Available command:
    list
        List tasks linked to /etc/gistore/tasks/

    status [task or direcotry]
        Show backup repository's backup list and other status

    init   [task or directory]
        Initial gistore backup repository

    commit [task or direcotry]
        Commit changes in backup repository. The following command run 
        in order:
          * mount
          * commit
          * umount

    mount  [task or direcotry]
        Mount 

    umount [task or direcotry]
        Umount
'''

import os
import sys
import getopt
import signal

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gistore.utils  import *
from gistore.config import *
from gistore.errors import *
from gistore.api    import Gistore
from gistore.versions import *

class GistoreCmd(object):
    opt_verbose = LOG_WARNING
    gistobj = None

    @staticmethod
    def do_mount(args=[]):
        if not args:
            args = [None]
        for repos in args:
            try:
                GistoreCmd.gistobj = Gistore(repos)
                GistoreCmd.gistobj.mount()
            except GistoreLockError, e:
                show_exception(e)
                continue

    @staticmethod
    def do_init(args=[]):
        if not args:
            args = [None]
        for repos in args:
            GistoreCmd.gistobj = Gistore(repos, True)
            GistoreCmd.gistobj.init()

    @staticmethod
    def do_list(args=[]):
        if not args:
            print "Task list:"
            tasksdir = os.path.join(cfg.sys_config_dir, 'tasks')
            if os.path.exists(tasksdir):
                for t in sorted(os.listdir(tasksdir)):
                    if t.startswith("."):
                        continue
                    dest = os.path.realpath(os.path.join(tasksdir,t))
                    print "    %-10s: %s" % (t, dest)
        else:
            GistoreCmd.do_status(args)

    @staticmethod
    def do_status(args=[]):
        if not args:
            args = [None]
        for repos in args:
            GistoreCmd.gistobj = Gistore(repos)
            GistoreCmd.gistobj.status()
            GistoreCmd.gistobj.post_check()

    @staticmethod
    def do_umount(args=[]):
        if not args:
            args = [None]
        for repos in args:
            try:
                GistoreCmd.gistobj = Gistore(repos)
                GistoreCmd.gistobj.umount()
            except GistoreLockError, e:
                show_exception(e)
                continue


    @staticmethod
    def do_commit_all(args=[]):
        tasks = []
        tasksdir = os.path.join(cfg.sys_config_dir, 'tasks')
        if os.path.exists(tasksdir):
            for t in sorted(os.listdir(tasksdir)):
                if t.startswith("."):
                    continue
                tasks.append(os.path.realpath(os.path.join(tasksdir,t)))
        if tasks:
            GistoreCmd.do_commit(tasks)


    @staticmethod
    def do_commit(args=[]):
        if not args:
            args = [None]
        for repos in args:
            try:
                GistoreCmd.gistobj = Gistore(repos)
                GistoreCmd.gistobj.mount()
                GistoreCmd.gistobj.commit()
                GistoreCmd.gistobj.umount()
                GistoreCmd.gistobj.post_check()
            except GistoreLockError, e:
                show_exception(e)
                continue

    @staticmethod
    def sigint_handler(signum, frame):
        """Do umount and others cleanups if receive SIGINT.
        """
        verbose("Catch SIGINT...", LOG_DEBUG)
        signal.signal(signal.SIGINT, signal.default_int_handler)
        GistoreCmd.cleanup()
        sys.exit(1)

    @staticmethod
    def cleanup():
        if GistoreCmd.gistobj is not None:
            verbose("Doing cleanups...", LOG_NOTICE)
            GistoreCmd.gistobj.cleanup()
        else:
            verbose("Not doing cleanups...", LOG_DEBUG)

    @staticmethod
    def usage(code, msg=''):
        if code:
            fd = sys.stderr
        else:
            fd = sys.stdout
        print >> fd, __doc__ % { 'PROGRAM':os.path.basename(sys.argv[0]) }
        if msg:
            print >> fd, msg
        sys.exit(code)

    @staticmethod
    def parse_options(argv):
        global cfg
        try:
            opts, args = getopt.getopt(
                argv, "hvq",
                [ "help", "verbose", "quiet" ])
        except getopt.error, msg:
            return GistoreCmd.usage(1, msg)

        for opt, arg in opts:
            if opt in ('-h', '--help'):
                return GistoreCmd.usage(0)
            elif opt in ('-v', '--verbose'):
                if GistoreCmd.opt_verbose < LOG_NOTICE:
                    GistoreCmd.opt_verbose = LOG_NOTICE
                else:
                    GistoreCmd.opt_verbose += 1
            elif opt in ('-q', '--quiet'):
                if GistoreCmd.opt_verbose > LOG_ERR:
                    GistoreCmd.opt_verbose = LOG_ERR
                else:
                    GistoreCmd.opt_verbose -= 1

        if GistoreCmd.opt_verbose is not None:
            cfg.log_level = GistoreCmd.opt_verbose

        return args

    @staticmethod
    def main(argv=None):
        # Parse global options...
        if argv is None:
            argv = sys.argv[1:]
        args = GistoreCmd.parse_options(argv)
        if not args:
            return GistoreCmd.usage(0)

        command = args[0].lower().replace('-','_')
        # Command aliases
        if command in ['unmount', 'umnt', 'unmnt']:
            command = 'umount'
        elif command in ['mnt']:
            command = 'mount'
        elif "initialized".startswith(command):
            command = 'init'
        elif command in ["ci", "checkin"]:
            command = 'commit'
        elif "status".startswith(command):
            command = 'status'
        elif command in ["ls", "dir"]:
            command = 'list'

        # Parse command options, and args is command params.
        args = GistoreCmd.parse_options(args[1:])

        try:
            # Override SIGINT handler, do umount and other cleanups...
            signal.signal(signal.SIGINT,  GistoreCmd.sigint_handler)
            signal.signal(signal.SIGHUP,  GistoreCmd.sigint_handler)
            signal.signal(signal.SIGQUIT, GistoreCmd.sigint_handler)
            signal.signal(signal.SIGABRT, GistoreCmd.sigint_handler)
            signal.signal(signal.SIGSEGV, GistoreCmd.sigint_handler)
            signal.signal(signal.SIGPIPE, GistoreCmd.sigint_handler)
            signal.signal(signal.SIGTERM, GistoreCmd.sigint_handler)

            if 'do_'+command in filter(lambda n: n.startswith('do_'), dir(GistoreCmd)):
                getattr(GistoreCmd, 'do_' + command)(args)
            else:
                return GistoreCmd.usage(1, "Unknown command: %s" % command)
        except GistoreLockError, e:
            raise e
        except Exception, e:
            show_exception(e)
            GistoreCmd.sigint_handler

def main(argv=None):
    GistoreCmd.main(argv)

if __name__ == '__main__':
	sys.exit(main())

# vim: et ts=4 sw=4
