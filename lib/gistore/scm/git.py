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
import re
import subprocess
import logging
import socket

from gistore.scm.abstract import AbstractSCM
from gistore.utils import *
from gistore.config import *

log = logging.getLogger('gist.git')

class SCM(AbstractSCM):

    GIT_DIR     = "repo.git"
    WORK_TREE   = "run-time"

    def __init__(self, root="", backup_history=0, backup_copies=0):
        super(SCM, self).__init__(root, backup_history, backup_copies)
        os.putenv("GIT_COMMITTER_NAME", self.username)
        os.putenv("GIT_COMMITTER_EMAIL", self.username+"@"+socket.gethostname())

    def get_command(self, git_dir=True, work_tree=True):
        args = [ "git" ]
        if git_dir:
            args.append( "--git-dir=%s" % os.path.join(self.root, self.GIT_DIR) )
        if work_tree:
            args.append( "--work-tree=%s" % os.path.join(self.root, self.WORK_TREE) )

        return args

    command = property(get_command)


    def is_repos(self):
        return os.path.exists( os.path.join(self.root, self.GIT_DIR, 'objects') )


    def init(self):
        if self.is_repos():
            log.warning("Repos %s already exists." % self.root)
            return False

        work_tree = os.path.join(self.root, self.WORK_TREE)
        if not os.path.exists(work_tree):
            os.makedirs(work_tree)

        commands = [ 
                    # git init command can not work with --work-tree arguments.
                    [ "git", "init", "--bare", os.path.join(self.root, self.GIT_DIR) ],

                    # a empty commit is used as root commit of rotate backup
                    self.command + [ "commit", "--allow-empty", "-m", "gistore root commit initialized." ],

                    # tag the empty commit as gistore/0, never delete it.
                    self.command + [ "tag", "gistore/0" ],

                    # set local git config, which not affect by global config
                    self.command + [ "config", "core.autocrlf", "false" ],
                    self.command + [ "config", "core.safecrlf", "false" ],
                    self.command + [ "config", "core.symlinks", "true" ],
                    self.command + [ "config", "core.trustctime", "false" ],
                    self.command + [ "config", "core.sharedRepository", "group" ],

                    # in case of merge, use ours instead.
                    self.command + [ "config", "merge.ours.name", "\"always keep ours\" merge driver" ],
                    self.command + [ "config", "merge.ours.driver", "touch %A" ],
                   ]

        for args in commands:
            log.debug(" ".join(args))
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
            exception_if_error(proc, args)

        log.debug("create .gitignore")
        fp = open(os.path.join(self.root, self.WORK_TREE, ".gitignore"), "w")
        fp.write(".gistore-*\n")
        fp.close()


    def upgrade(self, old):
        if old < 2:
            self.upgrade_2()


    def upgrade_2(self):
        if self.GIT_DIR != ".git":
            oldgit = os.path.join(self.root, ".git")
            if os.path.exists( oldgit ):
                os.rename( oldgit, os.path.join(self.root, self.GIT_DIR) )

        work_tree = os.path.join(self.root, self.WORK_TREE)
        if not os.path.exists(work_tree):
            os.makedirs(work_tree)

        commands = []
        args = self.command + [ "show-ref" ]
        returncode = subprocess.call( args=args, stdout=sys.stderr, close_fds=True )
        # repo.git has no commit yet
        if returncode != 0:
            commands += [
                          # a empty commit is used as root commit of rotate backup
                          self.command + [ "commit", "--allow-empty", "-m", "gistore root commit initialized." ],

                          # tag the empty commit as gistore/0, never delete it.
                          self.command + [ "tag", "gistore/0" ],
                         ]
        else:
            commands += [
                          # switch to a unexist ref
                          self.command + [ "symbolic-ref", "HEAD", "refs/tags/gistore/0" ],

                          # remove cached index
                          self.command + [ "rm", "--cached", "-r", "-f", "." ],

                          # a empty commit is used as root commit of rotate backup
                          self.command + [ "commit", "--allow-empty", "-m", "gistore root commit initialized." ],

                          # switch to master
                          self.command + [ "symbolic-ref", "HEAD", "refs/heads/master" ],
                          self.command + [ "reset", "HEAD" ],
                         ]

        commands +=[ 
                    # set as bare repos
                    self.command + [ "config", "core.bare", "true" ],

                    # set local git config, which not affect by global config
                    self.command + [ "config", "core.autocrlf", "false" ],
                    self.command + [ "config", "core.safecrlf", "false" ],
                    self.command + [ "config", "core.symlinks", "true" ],
                    self.command + [ "config", "core.trustctime", "false" ],
                    self.command + [ "config", "core.sharedRepository", "group" ],

                    # in case of merge, use ours instead.
                    self.command + [ "config", "merge.ours.name", "\"always keep ours\" merge driver" ],
                    self.command + [ "config", "merge.ours.driver", "touch %A" ],
                   ]

        for args in commands:
            log.debug(" ".join(args))
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
            exception_if_error(proc, args)


    def _get_commit_count(self):
        args = self.get_command(work_tree=False) + [ "rev-list", "master" ]
        log.debug(" ".join(args))
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=None, close_fds=True)
        lines = proc.stdout.readlines()
        proc.wait()
        if proc.returncode != 0:
            msg = "Last command: %s\n\tgenerate ERRORS with returncode %d!" % (cmdline, proc.returncode)
            log.critical( msg )
            if lines:
                log.critical( "Command output:\n" + ''.join(lines))
            raise CommandError( msg )

        log.debug( "Total %d commits in master." % len(lines) )
        return len(lines)


    def backup_rotate(self):
        if not self.backup_history or self.backup_history < 1:
            return
        if not self.backup_copies or self.backup_copies < 1:
            return

        count = self._get_commit_count()
        # the first commit is a blank commit
        if count < self.backup_history + 1:
            log.debug( "No backup rotate needed. %d < %d." % (count-1, self.backup_history) )
            return

        log.info( "Begin backup rotate, for %d >= %d." % (count-1, self.backup_history) )
        # list tags
        args = self.get_command(work_tree=False) + [ "tag" ]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=None, close_fds=True)
        lines = sorted(proc.stdout.readlines())
        proc.wait()
        if proc.returncode != 0:
            msg = "Last command: %s\n\tgenerate ERRORS with returncode %d!" % (cmdline, proc.returncode)
            log.critical( msg )
            if lines:
                log.critical( "Command output:\n" + ''.join(lines))
            raise CommandError( msg )
        tagids = []
        for tag in lines:
            tag=tag.strip()
            if not tag.startswith("gistore/"):
                continue
            try:
                tagN = int(tag[8:])
            except ValueError:
                continue
            if tagN == 0:
                continue
            tagids.append( tagN )

        command_list = []
        tagids = sorted( tagids )

        # rotate tags, and add new tag
        if len(tagids) >= self.backup_copies:
            for i in range(1, self.backup_copies):
                cmd = self.get_command(work_tree=False) + [ "tag", "-f", "gistore/%d" % i, "gistore/%d" % tagids[ i - self.backup_copies ] ]
                command_list.append(cmd)
            for i in tagids:
                if i in range(1, self.backup_copies):
                    continue
                cmd = self.get_command(work_tree=False) + [ "tag", "-d", "gistore/%d" % i ]
                command_list.append(cmd)
            cmd = self.get_command(work_tree=False) + [ "tag", "gistore/%d" % self.backup_copies, "master" ]
            command_list.append(cmd)
        else:
            if len(tagids) > 0:
                cmd = self.get_command(work_tree=False) + [ "tag", "gistore/%d" % (tagids[-1] + 1), "master" ]
            else:
                cmd = self.get_command(work_tree=False) + [ "tag", "gistore/1", "master" ]
            command_list.append(cmd)

        # reset master to gistore/0
        cmd = self.get_command(work_tree=False) + [ "update-ref", "refs/heads/master", "gistore/0" ]
        command_list.append(cmd)
        # do gc
        cmd = self.get_command(work_tree=False) + [ "gc" ]
        command_list.append(cmd)
        # reset HEAD
        cmd = self.get_command() + [ "reset", "HEAD" ]
        command_list.append(cmd)

        for i in range(len(command_list)):
            log.debug( "Backup rotate step %d: %s" % (i, ' '.join(command_list[i])) )
            proc = subprocess.Popen(command_list[i], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
            exception_if_error(proc, command_list[i])


    def commit(self, message=None):
        def commit_summary( commit_st ):
            sample = 5
            status = {}
            buffer = []
            for line in commit_st:
                k,v = line.split(None, 1)
                try:
                    status[k].append( v )
                except KeyError:
                    status[k] = [ v ]

            total = len( commit_st )
            buffer.append( "Changes summary: total= %(total)d, %(detail)s" % {
                    'total': total,
                    'detail': ", ".join( [ "%s: %d" % (k, len(status[k])) for k in sorted(status.keys()) ] ),
                    } )
            buffer.append( "-" * len(buffer[0]) )
            for k in sorted(status.keys()):
                brief_st = []
                total = len( status[k] )
                step = total // sample
                if step < 1:
                    brief_st = status[k]
                else:
                    for i in range(sample):
                        brief_st.append( status[k][i*step] )
                    brief_st.append( "...%d more..." % ( len(status[k]) - sample ) )
                buffer.append( "    %s => %s" % ( k, ", ".join(brief_st) ) )

            return "\n".join(buffer)

        self._abort_if_not_repos()

        # Check if backup needs rotate
        self.backup_rotate()

        args = self.command + [ "add", "." ]
        log.debug(" ".join(args))
        proc_add = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        exception_if_error(proc_add, args)

        if True:
            args = self.command + [ "ls-files", "--deleted" ]
            log.debug(" ".join(args))
            proc_ls = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
            deleted_files = []
            for file in proc_ls.stdout.readlines():
                # strip last CRLF
                file = file.rstrip()
                deleted_files.append(file)
            if deleted_files:
                try:
                    # `git rm --cached` will not remote blank-dir.
                    args = self.command + [ "rm", "--cached", "--quiet" ] + deleted_files
                    proc_rm = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
                    warn_if_error(proc_rm, args)
                except OSError, e:
                    if "Argument list too long" in e:
                        for file in deleted_files:
                            args = self.command + [ "rm", "--cached", "--quiet", file ]
                            proc_rm = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
                            warn_if_error(proc_rm, args)

        args = self.command + [ "status", "--porcelain" ]
        log.debug(" ".join(args))
        proc_st = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        commit_stat = []
        for line in proc_st.stdout.readlines():
            # strip last CRLF
            commit_stat.append( line.rstrip() )
       
        msgfile = os.path.join( self.root, GISTORE_LOG_DIR, "COMMIT_MSG" )
        fp = open( msgfile, "w" )
        if message:
            fp.write( message + "\n\n" )
        fp.write( commit_summary( commit_stat ) )
        fp.close()

        args = self.command + [ "commit", "--quiet", "-F", msgfile ]
        log.debug(" ".join(args))
        proc_ci = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        # If nothing to commit, git commit return 1.
        exception_if_error2( proc_ci, args, test=lambda n: n.startswith("nothing to commit") or n.startswith("no changes added to commit") )

    def post_check(self):
        submodules = []
        args = self.command + [ "submodule", "status", self.root]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        #Read stdout buffer before wait(), because if buffer overflow, process will hang!
        pat1 = re.compile(r".\w{40} (\w*) \(.*\)?")
        pat2 = re.compile(r"No submodule mapping found in .gitmodules for path '(.*)'")
        for line in proc.stdout.readlines():
            line = line.strip()
            m = pat1.match(line)
            if m:
                submodules.append(m.group(1))
            m = pat2.match(line)
            if m:
                submodules.append(m.group(1))
        if submodules:
            log.error("Not backup submodules:"+"\n    "+" ".join(submodules))
            log.error("    " + "* Remove submodules using command: git rm --cached sub/module")
        proc.wait()


# vim: et ts=4 sw=4
