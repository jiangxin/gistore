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

from subprocess import Popen, PIPE, STDOUT
import os
import sys
import getopt
import signal
from copy import deepcopy

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gistore.utils import *
from gistore.config import *
from gistore.errors import *


class Gistore(object):

    def __init__(self, task=None):
        self.root = None
        self.scm = None
        self.mounted = False

        self.cmd_mount = ["mount", "--rbind"]
        self.cmd_umount = ["umount"]
        self.cmd_umount_force = ["umount", "-f", "-l"]

        # Users other than root, may use other painless command
        if os.getuid() != 0:
            self.cmd_umount_force.insert(0, "sudo")
            if os.system("which bindfs >/dev/null 2>&1") == 0:
                self.cmd_mount = ["bindfs"]
                self.cmd_umount = ["fusermount","-u"]
            elif os.system("which sudo >/dev/null 2>&1") == 0:
                self.cmd_mount.insert(0, "sudo")
                self.cmd_umount.insert(0, "sudo")

        self.init_task(task)

    def init_task(self, taskname=None):
        """Set default root dir according to task name. Task name can be:
          * Task name in /etc/gistore/tasks/, which is a symbol link to real
            gistore backup directory
          * Absolute dir name, such as: /backup/store1/
          * Relative dir name from current working directory
        """
        if not taskname:
            taskname = os.getcwd()
        elif (not taskname.startswith('/') and
              not taskname.startswith('./') and
              not taskname.startswith('../') and
              taskname != '.' and
              taskname != '..'):
            path = os.path.join(cfg.sys_config_dir, "tasks", taskname)
            if os.path.exists(path):
                taskname = path
            else:
                taskname = os.path.join(os.getcwd(), taskname)

        self.root = os.path.realpath(taskname)

        # Taskname is the abbr. link dir name in /etc/gistore/tasks/
        self.taskname = self.dir2task(self.root)

        if not os.path.exists(self.root):
            os.makedirs(self.root)
        os.chdir(self.root)

        # Initail self.store_list from .gistore/config file.
        repo_cfg = self.parse_config()

        if os.getuid() != 0:
            if repo_cfg["root_only"]:
                raise PemissionDeniedError("Only root user allowed for task: %s" % (self.taskname or self.root))
            else:
                verbose("You are NOT root user, some backups may lost !", LOG_WARNING)

        # Scm backend initialized.
        scm = __import__("gistore.scm."+repo_cfg["backend"], globals(), {}, ["SCM"])
        self.scm = scm.SCM(self.root)


    def parse_config(self):
        """Initial self.store_list from cfg.store_list and .gistore/config file.
        """
        assert self.root

        repo_cfg = {"backend": cfg.backend,
                    "root_only": cfg.root_only }

        def update_config(config1, list2):
            config2 = {}
            if list2:
                for key, val in list2:
                    config2[key] = val
                    if val.lower() in ['0', 'f', 'false', 'n', 'no']:
                        config2[key] = False
                    elif val.lower() in ['1', 't', 'true', 'y', 'yes', 'ok']:
                        config2[key] = True
                config1.update(config2)

        def validate_list(dir_list):
            """Remove duplicate dirs and dir which is already a git repository.
            """
            targets = []
            for p in sorted(map(os.path.realpath, dir_list)):
                if os.path.exists(p):
                    # Remove duplicate path
                    if len(targets) and ( targets[-1] == p or
                       p.startswith(os.path.join(targets[-1],'')) ):
                        verbose("duplict path: %s" % p, LOG_WARNING)
                        continue

                    # check if already a git repos.
                    elif os.path.exists(os.path.join(p, '.git')):
                        if not os.access(os.path.join(p, '.git'), os.R_OK) or \
                           os.path.exists(os.path.join(p, '.git', 'objects')):
                            verbose("%s looks like a repository, and will add as submodule" % p, LOG_WARNING)

                    # check if p is parent of self.root
                    elif self.root.startswith(os.path.join(p,"")) or self.root == p:
                        verbose("Not store root's parent dir: %s" % p, LOG_WARNING)
                        continue

                    # check if p is child of self.root
                    elif p.startswith(os.path.join(self.root,"")):
                        if p != os.path.join(self.root, GISTORE_CONFIG_DIR):
                            verbose("Not store root's subdir: %s" % p, LOG_WARNING)
                            continue

                    targets.append(p)

                else:
                    verbose("%s not exists." % p, LOG_WARNING)

            return targets

        self.store_list = {}
        dir_list = cfg.store_list.get(self.taskname, [])
        default_config = {'keep_empty_dir': False, 'keep_perm': False, }
        config_file = os.path.join(self.root, GISTORE_CONFIG_DIR, "config")
        if os.path.exists(config_file):
            # backup .gistore config files
            dir_list.append(os.path.join(self.root, GISTORE_CONFIG_DIR))
            from ConfigParser import ConfigParser
            cp=ConfigParser()
            cp.read(config_file)
            if cp.has_option('main', 'backend'):
                repo_cfg["backend"] = cp.get('main', 'backend')
            if cp.has_option('main', 'root_only'):
                repo_cfg["root_only"] = cp.getboolean('main', 'root_only')
            if cp.has_section('default'):
                update_config(default_config, cp.items('default'))

            for section in filter(lambda n: n.startswith('store '), cp.sections()):
                dir_list.append(section[6:].strip())

            for path in validate_list(dir_list):
                self.store_list[path] = deepcopy(default_config)

            for section in filter(lambda n: n.startswith('store '), cp.sections()):
                path = os.path.realpath(section[6:].strip())
                if path in self.store_list.keys():
                    update_config(self.store_list[path], cp.items(section))

        else:
            for path in validate_list(dir_list):
                self.store_list[path] = deepcopy(default_config)

        return repo_cfg

    def is_mount(self, src, dest):
        """Check whether src is mount on dest.
        If mount using bindfs, check by os.path.ismount is ok.
        If mount using mount --bind, check by src and dest's inode.
        """
        try:
            stat1 = os.stat(src)
            stat2 = os.stat(dest)
        except:
            return False
        return stat1.st_ino == stat2.st_ino or os.path.ismount(dest)

    def task2dir(self, task):
        return os.path.realpath(os.path.join(cfg.sys_config_dir, 'tasks', task))

    def dir2task(self, path):
        tasksdir = os.path.join(cfg.sys_config_dir, 'tasks')
        if os.path.exists(tasksdir):
            for t in os.listdir(tasksdir):
                if os.path.realpath(os.path.join(tasksdir, t)) == os.path.realpath(path):
                    return t
        return None

    def status(self):
        print "Task name: ", self.taskname and self.taskname or "-"
        print "Directory: ", self.root
        print "Backup list:"
        for k,v in self.store_list.iteritems():
            print "    %s (%s%s)" % (
                    k,
                    v.get("keep_perm") and "P" or "-",
                    v.get("keep_empty_dir") and "K" or "-")

    def __mnt_target(self, p):
        if p == os.path.join(self.root, GISTORE_CONFIG_DIR):
            return os.path.join(self.root, GISTORE_CONFIG_DIR.rstrip('/')+"_history")
        else:
            return os.path.join(self.root, p.lstrip('/'))

    def mount(self):
        if self.store_list:
            self.mounted = True
        for p in self.store_list.keys():
            if os.path.isdir(p):
                target = self.__mnt_target(p)
                if not os.path.exists(target):
                    os.makedirs(target)
            elif os.path.isfile(p):
                target = self.__mnt_target(p)
                if not os.path.exists(os.path.dirname(target)):
                    os.makedirs(os.path.dirname(target))
                if not os.path.exists(target):
                    os.mknod(target, 0644)
            else:
                verbose("Unknown file type: %s." % p, LOG_ERR)
                continue

            if self.is_mount(p, target):
                verbose("%s is already mounted." % target, LOG_WARNING)
            else:
                args = self.cmd_mount + [p, target]
                verbose (" ".join(args), LOG_DEBUG)
                proc_mnt = Popen( self.cmd_mount + [p, target], stdout=PIPE, stderr=STDOUT, close_fds=True )
                exception_if_error(proc_mnt, args)

    def removedirs(self, target):
        target = os.path.realpath(target)
        if target == self.root:
            return
        try:
            #os.removedirs(target)
            os.rmdir(target)
        except:
            return
        self.removedirs(os.path.dirname(target))

    def umount(self):
        for p in self.store_list.keys():
            target = self.__mnt_target(p)
            if self.is_mount(p, target):
                args = self.cmd_umount + [target]
                verbose (" ".join(args), LOG_DEBUG)
                proc_umnt = Popen( self.cmd_umount + [target], stdout=PIPE, stderr=STDOUT, close_fds=True )
                warn_if_error(proc_umnt, args)
                if proc_umnt.returncode != 0:
                    args = self.cmd_umount_force + [target]
                    verbose (" ".join(args), LOG_DEBUG)
                    proc_umnt = Popen(args, stdout=PIPE, stderr=STDOUT, close_fds=True )
                    exception_if_error(proc_umnt, args)

                verbose ("remove %s" % target, LOG_DEBUG)
                if not self.is_mount(p, target):
                    if os.path.isdir(target):
                        self.removedirs(target)
                    else:
                        os.unlink(target)
                        self.removedirs(os.path.dirname(target))
        self.mounted = False

    def cleanup(self):
        if self.mounted:
            self.umount()


    def init(self):
        self.scm.init()
        config_file = os.path.join(self.root, GISTORE_CONFIG_DIR, "config")
        if not os.path.exists(config_file):
            os.mkdir(os.path.dirname(config_file))
            fp = open(config_file, "w")
            fp.write("""# Global config for all sections
[main]
#backend = git
#root_only = true

[default]
keep_perm = no
keep_empty_dir = no

# Define your backup list below. Section name begin with 'store ' will be backup.
# eg: [store /etc]
""")
            fp.close()


    def commit(self):
        self.scm.commit()

    def post_check(self):
        self.scm.post_check()



class GistoreCmd(object):
    opt_verbose = LOG_WARNING
    gistobj = None

    @staticmethod
    def do_mount(args=[]):
        if not args:
            args = [None]
        for repos in args:
            GistoreCmd.gistobj = Gistore(repos)
            GistoreCmd.gistobj.mount()

    @staticmethod
    def do_init(args=[]):
        if not args:
            args = [None]
        for repos in args:
            GistoreCmd.gistobj = Gistore(repos)
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
            GistoreCmd.gistobj = Gistore(repos)
            GistoreCmd.gistobj.umount()


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
            GistoreCmd.gistobj = Gistore(repos)
            GistoreCmd.gistobj.mount()
            GistoreCmd.gistobj.commit()
            GistoreCmd.gistobj.umount()
            GistoreCmd.gistobj.post_check()

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
        except Exception, e:
            show_exception(e)
            GistoreCmd.sigint_handler

def main(argv=None):
    GistoreCmd.main(argv)

if __name__ == '__main__':
	sys.exit(main())

# vim: et ts=4 sw=4
