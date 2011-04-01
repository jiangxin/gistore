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
import re
from subprocess import Popen, PIPE, STDOUT
from copy import deepcopy
import logging

from gistore.utils          import *
from gistore.config         import *
from gistore.repo_config    import RepoConfig
from gistore.errors         import *
from gistore                import versions

log = logging.getLogger('gist.api')

class Gistore(object):

    def __init__(self, task=None, create=False):
        self.root = None
        self.scm = None

        # Users other than root, try sudo.
        if os.getuid() != 0:
            self.runtime_dir = os.path.expanduser('~/.gistore.d/run/')
            if os.system("which sudo >/dev/null 2>&1") == 0:
                self.try_sudo = True
        else:
            self.runtime_dir = '/var/run/gistore/'
            self.try_sudo = False

        self.cmd_mount = []
        self.cmd_umount = []
        if os.system("which bindfs >/dev/null 2>&1") == 0:
            self.cmd_mount.append( ["bindfs", "-n"] )
            if self.try_sudo:
                # If use -n here, user cannot read the mounting file systems.
                self.cmd_mount.append( ["sudo", "bindfs"] )
        self.cmd_mount.append( ["mount", "--rbind"] )
        if self.try_sudo:
            self.cmd_mount.append( ["sudo", "mount", "--rbind"] )

        if os.system("which fusermount >/dev/null 2>&1") == 0:
            self.cmd_umount.append( ["fusermount","-u"] )
            if self.try_sudo:
                self.cmd_umount.append( ["sudo", "fusermount","-u"] )
        self.cmd_umount.append( ["umount"] )
        if self.try_sudo:
            self.cmd_umount.append( ["sudo", "umount"] )
        self.cmd_umount.append( ["umount", "-f"] )
        if self.try_sudo:
            self.cmd_umount.append( ["sudo", "umount", "-f"] )

        self.__init_task(task, create)

    def __init_task(self, taskname, create):
        """Set default root dir according to task name. Task name can be:
          * Task name in $HOME/.gistore.d/tasks/ or /etc/gistore/tasks (for root
            user), which is a symbol link to real gistore backup directory.
          * Absolute dir name, such as: /backup/store1/.
          * Relative dir name from current working directory.
        """
        if not taskname:
            taskname = os.getcwd()
        elif (not taskname.startswith('/') and
              not taskname.startswith('./') and
              not taskname.startswith('../') and
              taskname != '.' and
              taskname != '..'):
            path = os.path.join(cfg.tasks_dir, taskname)
            if os.path.exists(path):
                taskname = path
            else:
                taskname = os.path.join(os.getcwd(), taskname)

        self.root = os.path.realpath(taskname)

        if create:
            if ( os.path.exists( self.root ) and
                 len ( os.listdir(self.root) ) > 0 ):
                raise TaskAlreadyExistsError(
                            "Not a empty directory: %s" % ( self.root) )
        elif not os.path.exists( os.path.join( self.root,
                                               GISTORE_CONFIG_DIR,
                                               "config") ):
                raise TaskNotExistsError( "Task does not exists: %s." % (
                                          os.path.join( self.root,
                                                        GISTORE_CONFIG_DIR,
                                                        "config") ) )

        # Create needed directories
        check_dirs = [ os.path.join( self.root, GISTORE_LOG_DIR ),
                       os.path.join( self.root, GISTORE_LOCK_DIR ),
                       os.path.join( self.root, GISTORE_CONFIG_DIR ) ]
        for dir in check_dirs:
            if not os.path.exists( dir ):
                os.makedirs( dir )

        # Set file log
        filelog = logging.FileHandler( os.path.join( self.root,
                                                     GISTORE_LOG_DIR,
                                                     "gitstore.log" ) )
        filelog.setLevel( cfg.log_level )
        # set a format which is simpler for filelog use
        formatter = logging.Formatter(
                        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
                        )
        filelog.setFormatter(formatter)
        # add the handler to the root logger
        logging.getLogger('').addHandler(filelog)


        # Taskname is the abbr. link dir name in $HOME/.gistore.d/tasks
        # or /etc/gistore/tasks/ for root user.
        self.taskname = self.dir2task(self.root)

        # Initail self.store_list from .gistore/config file.
        self.parse_config()
        old_version = int(self.rc.repo_cfg["main.version"])

        # Upgrade config file if needed.
        if old_version is not None and old_version != versions.GISTORE_VERSION:
            self.upgrade(old_version)

        # Scm backend initialized.
        scm = __import__( "gistore.scm."+self.rc.repo_cfg["main.backend"],
                          globals(), {}, ["SCM"] )
        self.WORK_TREE = os.path.realpath(
                            os.path.join( self.runtime_dir,
                                          ( self.taskname or
                                            os.path.basename( self.root ) ),
                                          str( os.getpid() ) ) )
        self.scm = scm.SCM(self.root,
                        work_tree=self.WORK_TREE,
                        backup_history=self.rc.repo_cfg["main.backuphistory"],
                        backup_copies=self.rc.repo_cfg["main.backupcopies"])

        # Upgrade scm if needed.
        if old_version is not None and old_version != versions.GISTORE_VERSION:
            self.scm.upgrade(old_version)

        # Check uid
        if os.getuid() != 0:
            if self.rc.repo_cfg["main.rootonly"] == 'true':
                raise PemissionDeniedError(
                    "Only root user allowed for task: %s" % (
                    self.taskname or self.root))



    def init(self):
        self.scm.init()
        self.rc.save()

    def log(self, args=[]):
        self.scm.log(args)

    def upgrade(self, oldversion):
        if oldversion == versions.GISTORE_VERSION:
            return

        if oldversion < 2:
            self.upgrade_2(gistore_config)


    def upgrade_2(self, gistore_config):
        self.rc.add("main.version", 2)


    def parse_config(self):
        """Initial self.store_list from cfg.store_list and .gistore/config file.
        """
        def validate_list(store_list):
            """Remove duplicate dirs.
            """
            targets = []
            dir_list = filter( lambda n: not store_list[n].has_key('enabled') or
                               store_list[n]['enabled'] in ['true', 'yes'],
                               store_list.keys() )
            for p in sorted(map(os.path.realpath, dir_list)):
                if os.path.exists(p):
                    # Remove duplicate path
                    if len(targets) and ( targets[-1] == p or
                       p.startswith(os.path.join(targets[-1],'')) ):
                        log.warning("duplict path: %s" % p)
                        continue

                    # check if p is parent of self.root
                    elif ( self.root.startswith(os.path.join(p,"")) or
                           self.root == p ):
                        log.error("Not store root's parent dir: %s" % p)
                        continue

                    # check if p is child of self.root
                    elif p.startswith(os.path.join(self.root,"")):
                        if p != os.path.join(self.root, GISTORE_CONFIG_DIR):
                            log.error("Not store root's subdir: %s" % p)
                            continue

                    targets.append(p)

                else:
                    log.warning("%s not exists." % p)

            return targets

        self.store_list = {}
        store_list = {}

        config_file = os.path.join(self.root, GISTORE_CONFIG_DIR, "config")
        self.rc = RepoConfig( config_file )

        dir_list = cfg.store_list.get(self.taskname, [])
        # backup .gistore config files
        dir_list.append(os.path.join(self.root, GISTORE_CONFIG_DIR))

        for path in dir_list:
            store_list[path] = self.rc.defaults.copy()
            store_list[path]["system"] = 'true'
            store_list[path]["enabled"] = 'true'

        for rawkey in filter( lambda n: n.startswith('store.'), self.rc.repo_cfg.keys() ):
            section, key = rawkey.rsplit('.', 1)
            section = os.path.realpath(section[6:])
            key = key.lower()
            if not store_list.has_key( section ):
                store_list[section] = self.rc.defaults.copy()
            store_list[section][key] = self.rc.repo_cfg[rawkey]

        for path in validate_list(store_list):
            self.store_list[path] = store_list[path]


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
        return os.path.realpath(os.path.join(cfg.tasks_dir, task))

    def dir2task(self, path):
        if os.path.exists(cfg.tasks_dir):
            for t in os.listdir(cfg.tasks_dir):
                if os.path.realpath(os.path.join(cfg.tasks_dir, t)) == os.path.realpath(path):
                    return t
        return None

    def status(self):
        print "%18s : %s" % ("Task name",
                self.taskname and self.taskname or "-")
        print "%18s : %s" % ("Directory", self.root)
        print "%18s : %s" % ("Backend", self.rc.repo_cfg["main.backend"])
        print "%18s : %s commits * %s copies" %  ( "Backup capability",
                self.rc.repo_cfg["main.backuphistory"],
                self.rc.repo_cfg["main.backupcopies"] )
        print "%18s :" % "Backup list"
        for k,v in sorted(self.store_list.iteritems()):
            print " " * 18 + "   %s (%s%s)" % (
                    k,
                    v.get("keepperm") == 'true' and "A" or "-",
                    v.get("keepemptydir") == 'true' and "D" or "-")

    def __mnt_target(self, p):
        if os.path.realpath(p) == os.path.realpath( os.path.join( self.root,
                                                    GISTORE_CONFIG_DIR ) ):
            return os.path.join( self.WORK_TREE,
                                 GISTORE_CONFIG_DIR.rstrip('/') )
        else:
            return os.path.join( self.WORK_TREE, p.lstrip('/') )

    def mount(self):
        self.lock("mount")

        # Create work_tree if not exists.
        if not os.path.exists( self.WORK_TREE ):
            try:
                os.makedirs( self.WORK_TREE, mode=0777 )
            except OSError:
                raise PemissionDeniedError("Can not create run-time dir: %s. You can override it in config file." % self.WORK_TREE)

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
                log.error("Mount failed. Unknown file type: %s." % p)
                continue

            if self.is_mount(p, target):
                log.warning("%s is already mounted." % target)
            else:
                mounted = False
                for command in self.cmd_mount:
                    proc_mnt = Popen( command + [ p, target ],
                                      stdout=PIPE,
                                      stderr=STDOUT )
                    try:
                        (stdout, stderr) = communicate( proc_mnt,
                                                        command + [ p, target ],
                                                        verbose=False )
                    except:
                        mounted = False
                    else:
                        mounted = True
                        break
                if not mounted:
                    msg = "Last command: %s\n\tgenerate ERRORS with returncode %d!" % (
                                " ".join(command+ [ p, target ]),
                                proc_mnt.returncode )
                    log.critical( msg )
                    if stdout:
                        log.warning( "Command output:\n" + stdout )
                    if stderr:
                        log.warning( "Command error output:\n" + stderr )

                    raise CommandError( msg )

    def removedirs(self, target):
        target = os.path.realpath(target)
        if target == os.path.realpath(self.runtime_dir):
            return
        try:
            os.rmdir(target)
        except:
            return
        self.removedirs(os.path.dirname(target))

    def umount(self):
        self.assert_no_lock("commit")

        proc = Popen( [ "mount" ],
                        stdout=PIPE,
                        stderr=STDOUT )
        output = communicate(proc, "mount")[0]
        pattern = re.compile(r"^(.*) on (.*?) (type |\().*$")
        mount_list = []
        for line in output.splitlines():
            m = pattern.search(line)
            if m:
                src = m.group(1)
                target = os.path.realpath( m.group(2) )
                if target.startswith( self.WORK_TREE ):
                    mount_list.append( (target, src, ) )

        for target, src in sorted( mount_list, reverse=True ):
            umounted = False
            stdout, stderr = None, None
            for command in self.cmd_umount:
                proc_umnt = Popen( command + [ target ],
                                   stdout=PIPE,
                                   stderr=STDOUT )
                try:
                    (stdout, stderr) = communicate( proc_umnt,
                                                    command + [ target ],
                                                    ignore=lambda n: n.endswith("not mounted"),
                                                    verbose=False )
                except:
                    umounted = False
                else:
                    umounted = True
                    break

            if not umounted:
                msg = "Last command: %s\n\tgenerate ERRORS with returncode %d!" % (
                            " ".join(command + [ target ]),
                            proc_umnt.returncode )
                log.critical( msg )
                if stdout:
                    log.warning( "Command output:\n" + stdout )
                if stderr:
                    log.warning( "Command error output:\n" + stderr )

                raise CommandError( msg )

        for target, src in sorted( mount_list, reverse=True ):
            log.debug("remove %s" % target)
            if ( not self.is_mount(src, target)
                 and target.startswith( self.WORK_TREE )
                 and target != self.WORK_TREE ):
                if os.path.isdir(target):
                    self.removedirs(target)
                else:
                    os.unlink(target)
                    target = os.path.dirname( target )
                    if ( target.startswith( self.WORK_TREE )
                         and target != self.WORK_TREE ):
                        self.removedirs( target )

        self.unlock("mount")


    def cleanup(self):
        self.unlock("commit")
        self.umount()

    def commit(self, message):
        self.assert_lock("mount")
        self.lock("commit")
        self.scm.commit( message )
        self.unlock("commit")

    def post_check(self):
        self.scm.post_check()

    def has_lock(self, event):
        lockfile = os.path.join( self.root,
                                 GISTORE_LOCK_DIR,
                                 "_gistore-lock-" + event )
        if os.path.exists( lockfile ):
            return True
        else:
            return False

    def lock(self, event):
        self.assert_no_lock(event)

        lockfile = os.path.join( self.root,
                                 GISTORE_LOCK_DIR,
                                 "_gistore-lock-" + event )
        f = open( lockfile, 'w' )
        f.write( str( os.getpid() ) )
        f.close()

    def assert_lock(self, event):
        lockfile = os.path.join( self.root,
                                 GISTORE_LOCK_DIR,
                                 "_gistore-lock-" + event )
        if not os.path.exists( lockfile ):
            raise GistoreLockError( "Has not lock using: %s" % lockfile )

    def assert_no_lock(self, event):
        lockfile = os.path.join( self.root,
                                 GISTORE_LOCK_DIR,
                                 "_gistore-lock-" + event )
        if os.path.exists( lockfile ):
            raise GistoreLockError( "Lock already exists: %s" % lockfile )

    def unlock(self, event):
        lockfile = os.path.join( self.root,
                                 GISTORE_LOCK_DIR,
                                 "_gistore-lock-" + event )
        try:
            os.unlink( lockfile )
        except OSError:
            pass

    def add(self, args=[]):
        for path in args:
            key = "store.%s.enabled" % os.path.realpath(path)
            self.rc.add(key, "true")


    def rm(self, args=[]):
        for path in args:
            keys = [ "store.%s.enabled" % os.path.realpath(path) ]
            if os.path.realpath(path) != path:
                keys.append( "store.%s.enabled" % path )
            for key in keys:
                if self.rc.repo_cfg.has_key( key ):
                    if self.rc.repo_cfg[ key ] == 'true':
                        self.rc.add(key, 'false')
                        break
                self.rc.remove_section( key.rsplit('.',1)[0] )


# vim: et ts=4 sw=4
