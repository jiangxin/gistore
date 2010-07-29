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

from gistore.scm.abstract import AbstractSCM
from gistore.utils import *
from gistore.config import *

class SCM(AbstractSCM):

    GIT_DIR     = "repo.git"
    WORK_TREE   = "run-time"

    def get_command(self):
        return [ "git",
                 "--git-dir=%s" % os.path.join(self.root, self.GIT_DIR),
                 "--work-tree=%s" % os.path.join(self.root, self.WORK_TREE),
               ]

    command = property(get_command)


    def is_repos(self):
        return os.path.exists( os.path.join(self.root, self.GIT_DIR, 'objects') )


    def init(self):
        if self.is_repos():
            verbose("Repos %s already exists." % self.root, LOG_WARNING)
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
            verbose(" ".join(args), LOG_DEBUG)
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
            exception_if_error(proc, args)

        verbose("create .gitignore", LOG_DEBUG)
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
            verbose(" ".join(args), LOG_DEBUG)
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
            exception_if_error(proc, args)


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

        args = self.command + [ "add", "." ]
        verbose(" ".join(args), LOG_DEBUG)
        proc_add = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        exception_if_error(proc_add, args)

        if True:
            args = self.command + [ "ls-files", "--deleted" ]
            verbose(" ".join(args), LOG_DEBUG)
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
        verbose(" ".join(args), LOG_DEBUG)
        proc_st = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        commit_stat = []
        for line in proc_st.stdout.readlines():
            # strip last CRLF
            commit_stat.append( line.rstrip() )
       
        msgfile = os.path.join( self.root, GISTORE_LOG_DIR, "_gistore-commit-log" )
        fp = open( msgfile, "w" )
        if message:
            fp.write( message + "\n\n" )
        fp.write( commit_summary( commit_stat ) )
        fp.close()

        username = os.getlogin() or "gistore"
        import socket
        os.putenv("GIT_COMMITTER_NAME", username)
        os.putenv("GIT_COMMITTER_EMAIL", username+"@"+socket.gethostname())

        args = self.command + [ "commit", "--quiet", "-F", msgfile ]
        verbose(" ".join(args), LOG_DEBUG)
        proc_ci = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        # If nothing to commit, git commit return 1.
        exception_if_error2(proc_ci, args, test=lambda n: n.startswith("nothing to commit"))

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
            verbose("Not backup submodules:"+"\n    "+" ".join(submodules), LOG_ERR, False)
            verbose("    " + "* Remove submodules using command: git rm --cached sub/module", LOG_ERR, False)
        proc.wait()


# vim: et ts=4 sw=4
