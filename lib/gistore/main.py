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
        List tasks linked to $HOME/.gistore.d/tasks or
        /etc/gistore/tasks/ for root user.

    status [task or direcotry]
        Show backup repository's backup list and other status

    init   [task or directory]
        Initial gistore backup repository

    commit [-m message] [task or direcotry ...]
        Commit changes in backup repository. The following command run
        in order:
          * mount
          * commit
          * umount

    commit-all [-m message]
        Commit changes in all backup tasks under /etc/gistore/tasks/

    add path, ...
        Add backup items.

    rm path, ...
        Remove backup items.

    log [options...]
        Show backup logs.
'''

import os
import sys
import getopt
import signal
import logging

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gistore.utils  import *
from gistore.config import *
from gistore.errors import *
from gistore.api    import Gistore
from gistore.versions import *

log = logging.getLogger('gist.main')

def get_log_level( level ):
    try:
        level = int( level )
    except ValueError:
        level = logging._levelNames.get ( level.upper(), logging.DEBUG )

    if level <= 9:
        if level >= 5:
            level = logging.DEBUG
        elif level >= 4:
            level = logging.INFO
        elif level >= 3:
            level = logging.WARNING
        elif level >= 2:
            level = logging.ERROR
        elif level <= 1:
            level = logging.CRITICAL

    # level is number and >= 10
    elif not logging._levelNames.has_key( level ):
        level = logging.DEBUG

    return level


class GistoreCmd(object):
    opt_verbose = 4     # info

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
                logging.critical( get_exception(e) )
                continue

    @staticmethod
    def do_init(args=[]):
        if not args:
            args = [None]
        for repos in args:
            try:
                GistoreCmd.gistobj = Gistore(repos, True)
                GistoreCmd.gistobj.init()
            except GistoreLockError, e:
                logging.critical( get_exception(e) )
                continue
            except Exception, e:
                logging.critical( get_exception(e) )
                # remove lock files...
                GistoreCmd.cleanup()
                continue


    @staticmethod
    def do_list(args=[]):
        if not args:
            print "Task list:"
            if os.path.exists(cfg.tasks_dir):
                for t in sorted(os.listdir(cfg.tasks_dir)):
                    if t.startswith("."):
                        continue
                    dest = os.path.realpath(os.path.join(cfg.tasks_dir,t))
                    print "    %-10s: %s" % (t, dest)
        else:
            GistoreCmd.do_status(args)


    @staticmethod
    def do_status(args=[]):
        if not args:
            args = [None]
        for repos in args:
            try:
                GistoreCmd.gistobj = Gistore(repos)
                GistoreCmd.gistobj.status()
                GistoreCmd.gistobj.post_check()
            except Exception, e:
                logging.critical( get_exception(e) )
                continue


    @staticmethod
    def do_add(args=[]):
        if not args:
            args = [None]
        if len(args) == 1:
            repos = None
        else:
            repos = args[0]
            args = args[1:]
        try:
            GistoreCmd.gistobj = Gistore(repos)
            GistoreCmd.gistobj.add(args)
        except Exception, e:
            logging.critical( get_exception(e) )


    @staticmethod
    def do_rm(args=[]):
        if not args:
            args = [None]
        if len(args) == 1:
            repos = None
        else:
            repos = args[0]
            args = args[1:]
        try:
            GistoreCmd.gistobj = Gistore(repos)
            GistoreCmd.gistobj.rm(args)
        except Exception, e:
            logging.critical( get_exception(e) )


    @staticmethod
    def do_umount(args=[]):
        if not args:
            args = [None]
        for repos in args:
            try:
                GistoreCmd.gistobj = Gistore(repos)
                GistoreCmd.gistobj.umount()
            except GistoreLockError, e:
                logging.critical( get_exception(e) )
                continue
            except Exception, e:
                logging.critical( get_exception(e) )
                GistoreCmd.cleanup()
                continue

    @staticmethod
    def do_forbidden(args=[]):
        raise Exception("Internal use only, not run by user.")

    @staticmethod
    def do_commit_all(args=[]):
        tasks = []
        if os.path.exists(cfg.tasks_dir):
            for t in sorted(os.listdir(cfg.tasks_dir)):
                if t.startswith("."):
                    continue
                tasks.append(os.path.realpath(os.path.join(cfg.tasks_dir,t)))
        if tasks:
            GistoreCmd.do_commit( args + tasks )


    @staticmethod
    def do_commit(argv=[]):
        commit_msg = None
        try:
            opts, args = getopt.getopt(
                argv, "m:",
                [ "message" ])
        except getopt.error, msg:
            return GistoreCmd.usage(1, msg)

        for opt, arg in opts:
            if opt in ('-m', '--message'):
                commit_msg = arg

        if not args:
            args = [None]
        for repos in args:
            try:
                GistoreCmd.gistobj = Gistore(repos)
                GistoreCmd.gistobj.mount()
                GistoreCmd.gistobj.commit( commit_msg )
                GistoreCmd.gistobj.umount()
                GistoreCmd.gistobj.post_check()
            except GistoreLockError, e:
                logging.critical( get_exception(e) )
                continue
            except TaskNotExistsError, e:
                logging.critical( get_exception(e) )
                continue
            except Exception, e:
                logging.critical( get_exception(e) )
                # remove lock files...
                GistoreCmd.cleanup()
                continue


    @staticmethod
    def do_log(args=[]):
        repos = None
        if args and not args[0].startswith('-'):
            repos = args[0]
            args = args[1:]

        try:
            GistoreCmd.gistobj = Gistore(repos)
            GistoreCmd.gistobj.log(args)
        except Exception, e:
            logging.critical( get_exception(e) )


    @staticmethod
    def sigint_handler(signum, frame):
        """Do umount and others cleanups if receive SIGINT.
        """
        log.critical("Catch SIGINT. Cleanup then exit...")
        GistoreCmd.cleanup()
        signal.signal(signal.SIGINT, signal.default_int_handler)
        sys.exit(1)

    @staticmethod
    def cleanup():
        if GistoreCmd.gistobj is not None:
            log.warning("Doing cleanups...")
            GistoreCmd.gistobj.cleanup()
        else:
            log.debug("Not doing cleanups...")

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
                if GistoreCmd.opt_verbose >= 5:
                    GistoreCmd.opt_verbose = 5
                else:
                    GistoreCmd.opt_verbose += 1
            elif opt in ('-q', '--quiet'):
                if GistoreCmd.opt_verbose <= 0:
                    GistoreCmd.opt_verbose = 0
                else:
                    GistoreCmd.opt_verbose -= 1

        if GistoreCmd.opt_verbose is not None:
            cfg.log_level = GistoreCmd.opt_verbose
        cfg.log_level = get_log_level(cfg.log_level)

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
        if command in ['umount', 'unmount', 'umnt', 'unmnt']:
            command = 'forbidden'
        elif command in ['mount', 'mnt']:
            command = 'forbidden'
        elif "initialized".startswith(command):
            command = 'init'
        elif command in ["ci", "backup"]:
            command = 'commit'
        elif command in ["ci_all", "backup_all"]:
            command = 'commit_all'
        elif "status".startswith(command):
            command = 'status'
        elif command in ["ls", "dir"]:
            command = 'list'

        # Command args
        args = args[1:]

        # Set logging basic config, to stderr
        logging.basicConfig( level=cfg.log_level,
                format='%(asctime)s %(levelname)-8s %(message)s',
                datefmt='%m-%d %T')

        try:
            # Override SIGINT handler, do umount and other cleanups...
            signal.signal(signal.SIGINT,  GistoreCmd.sigint_handler)
            signal.signal(signal.SIGHUP,  GistoreCmd.sigint_handler)
            signal.signal(signal.SIGQUIT, GistoreCmd.sigint_handler)
            signal.signal(signal.SIGABRT, GistoreCmd.sigint_handler)
            signal.signal(signal.SIGSEGV, GistoreCmd.sigint_handler)
            signal.signal(signal.SIGPIPE, GistoreCmd.sigint_handler)
            signal.signal(signal.SIGTERM, GistoreCmd.sigint_handler)

            if 'do_'+command in filter( lambda n: n.startswith('do_'),
                                        dir(GistoreCmd) ):
                getattr(GistoreCmd, 'do_' + command)(args)
            else:
                return GistoreCmd.usage(1, "Unknown command: %s" % command)
        except GistoreLockError, e:
            logging.critical( str(e) )
            raise e
        except Exception, e:
            logging.critical( get_exception(e) )
            GistoreCmd.sigint_handler

def main(argv=None):
    GistoreCmd.main(argv)

if __name__ == '__main__':
	sys.exit(main())

# vim: et ts=4 sw=4
