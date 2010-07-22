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
import sys
from subprocess import Popen, PIPE, STDOUT
from copy import deepcopy

from gistore.utils  import *
from gistore.config import *
from gistore.errors import *
from gistore        import versions

class Gistore(object):

    def __init__(self, task=None, create=False):
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

        self.__init_task(task, create)

    def __init_task(self, taskname, create):
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

        if create:
            if os.path.exists( self.root ):
                raise TaskAlreadyExistsError("Task already exists in: %s." % self.root)
            else:
                os.makedirs(self.root)
        elif not os.path.exists( os.path.join(self.root, GISTORE_CONFIG_DIR, "config") ):
                raise TaskNotExistsError("Task does not exists: %s." % os.path.join(self.root, GISTORE_CONFIG_DIR, "config") )

        os.chdir(self.root)

        # Taskname is the abbr. link dir name in /etc/gistore/tasks/
        self.taskname = self.dir2task(self.root)

        # Initail self.store_list from .gistore/config file.
        repo_cfg = self.parse_config()
        old_version = repo_cfg["main.version"]

        # Upgrade config file if needed.
        if old_version is not None and old_version != versions.GISTORE_VERSION:
            self.upgrade(repo_cfg)

        # Scm backend initialized.
        scm = __import__("gistore.scm."+repo_cfg["main.backend"], globals(), {}, ["SCM"])
        self.scm = scm.SCM(self.root)

        # Upgrade scm if needed.
        if old_version is not None and old_version != versions.GISTORE_VERSION:
            self.scm.upgrade(old_version)

        if os.getuid() != 0:
            if repo_cfg["main.root_only"]:
                raise PemissionDeniedError("Only root user allowed for task: %s" % (self.taskname or self.root))
            else:
                verbose("You are NOT root user, some backups may lost !", LOG_WARNING)


    def init(self):
        self.scm.init()
        repo_cfg = {
                    "main.backend": cfg.backend,
                    "main.root_only": cfg.root_only,
                    "main.version": versions.GISTORE_VERSION,
                    'default.keep_empty_dir': False,
                    'default.keep_perm': False,
                   }
        self.save_config(repo_cfg)


    def upgrade(self, gistore_config):
        oldversion = gistore_config["main.version"]
        if oldversion == versions.GISTORE_VERSION:
            return
        
        if oldversion < 2:
            self.upgrade_2(gistore_config)

        self.save_config(gistore_config)


    def upgrade_2(self, gistore_config):
        gistore_config["main.version"] = 2


    def save_config(self, gistore_config={}):
        config_file = os.path.join(self.root, GISTORE_CONFIG_DIR, "config")
        if not os.path.exists(config_file):
            os.mkdir(os.path.dirname(config_file))

        main_buffer = []
        default_buffer = []
        for key, val in sorted(gistore_config.iteritems()):
            if key.startswith("default."):
                default_buffer.append( "%s = %s" % (
                         key[8:],
                         isinstance(val, bool) and ( val and "yes" or "no") or val,
                         ) )
            elif key.startswith("main."):
                main_buffer.append( "%s = %s" % (
                         key[5:],
                         isinstance(val, bool) and ( val and "yes" or "no") or val,
                         ) )

        store_buffer = []
        print self.store_list
        for path in sorted(self.store_list.keys()):
            if self.store_list[path].get('_system_', False):
                continue
            store_buffer.append( "[store %s]" % path )

            for key, val in self.store_list[path].iteritems():
                if gistore_config.get("default."+key, None) == val:
                    continue

                if isinstance(val, bool):
                    store_buffer.append( "%(key)s = %(val)s" % {
                            "key": key,
                            "val": val and "yes" or "no",
                            } )
                else:
                    store_buffer.append( key + " = " + val )
            store_buffer.append( "" )



        fp = open(config_file, "w")
        fp.write("""# Global config for all sections
[main]
%(main)s

[default]
%(default)s

# Define your backup list below. Section name begin with 'store ' will be backup.
# eg: [store /etc]
%(store)s
""" %       {
             'main':    "\n".join(main_buffer),
             'default': "\n".join(default_buffer),
             'store':   "\n".join(store_buffer),
            }
        )

        fp.close()


    def parse_config(self):
        """Initial self.store_list from cfg.store_list and .gistore/config file.
        """
        assert self.root

        repo_cfg = {
                    "main.backend": cfg.backend,
                    "main.root_only": cfg.root_only,
                    "main.version": None,
                    'default.keep_empty_dir': False,
                    'default.keep_perm': False,
                   }

        def update_config(config1, list2, prefix=""):
            config2 = {}
            if list2:
                for key, val in list2:
                    config2[prefix + key] = val
                    if val.lower() in ['0', 'f', 'false', 'n', 'no']:
                        config2[prefix + key] = False
                    elif val.lower() in ['1', 't', 'true', 'y', 'yes', 'ok']:
                        config2[prefix + key] = True
                config1.update(config2)

        def get_default(config1):
            config2 = {}
            for key, val in config1.iteritems():
                if not key.startswith("default."):
                    continue
                config2[key[8:]] = val
            return config2

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
        config_file = os.path.join(self.root, GISTORE_CONFIG_DIR, "config")
        if os.path.exists(config_file):
            # backup .gistore config files
            dir_list.append(os.path.join(self.root, GISTORE_CONFIG_DIR))
            from ConfigParser import ConfigParser
            cp=ConfigParser()
            cp.read(config_file)
            if cp.has_option('main', 'backend'):
                repo_cfg["main.backend"] = cp.get('main', 'backend')
            if cp.has_option('main', 'root_only'):
                repo_cfg["main.root_only"] = cp.getboolean('main', 'root_only')
            if cp.has_option('main', 'version'):
                repo_cfg["main.version"] = cp.getint('main', 'version')
            else:
                # old version, needs to upgrade
                repo_cfg["main.version"] = 1

            if cp.has_section('default'):
                update_config(repo_cfg, cp.items('default'), "default.")

            for path in validate_list(dir_list):
                self.store_list[path] = get_default(repo_cfg)
                self.store_list[path]["_system_"] = True

            for section in filter(lambda n: n.startswith('store '), cp.sections()):
                self.store_list[section[6:].strip()] = get_default(repo_cfg)

            for section in filter(lambda n: n.startswith('store '), cp.sections()):
                path = os.path.realpath(section[6:].strip())
                if path in self.store_list.keys():
                    update_config(self.store_list[path], cp.items(section))

        else:
            for path in validate_list(dir_list):
                self.store_list[path] = get_default(repo_cfg)
                self.store_list[path]["_system_"] = True

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

    def commit(self):
        self.scm.commit()

    def post_check(self):
        self.scm.post_check()


# vim: et ts=4 sw=4
