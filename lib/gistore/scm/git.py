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


    def __init__( self, root="",
                  work_tree="run-time",
                  backup_history=0,
                  backup_copies=0 ):
        super(SCM, self).__init__( root,
                                   work_tree,
                                   backup_history,
                                   backup_copies )
        os.putenv( "GIT_COMMITTER_NAME", self.username )
        os.putenv( "GIT_COMMITTER_EMAIL",
                   self.username+"@"+socket.gethostname() )
        # Not affect by info/grafts
        os.putenv( "GIT_GRAFT_FILE", "info/grafts-%s-tmp" % os.getpid() )
        self.GIT_DIR = "repo.git"
        args = [ 'which', 'git' ]
        proc = subprocess.Popen( args, stdout=subprocess.PIPE, stderr=None )
        self.gitcmd = communicate(proc, args)[0].strip()

    def get_command( self, git_dir=True, work_tree=True ):
        args = [ self.gitcmd ]
        if git_dir:
            args.append( "--git-dir=%s" % os.path.join( self.root,
                                                        self.GIT_DIR) )
        if work_tree:
            args.append( "--work-tree=%s" % os.path.join( self.root,
                                                          self.WORK_TREE) )

        return args

    command = property(get_command)


    def is_repos(self):
        return os.path.exists( os.path.join( self.root,
                                             self.GIT_DIR,
                                             'objects') )


    def init(self):
        if self.is_repos():
            log.warning("Repos %s already exists." % self.root)
            return False

        commands = [ 
                    # git init command can not work with --work-tree arguments.
                    [ self.gitcmd,
                      "--git-dir=%s" % os.path.join( self.root, self.GIT_DIR ),
                      "init",
                      "--bare", ],

                    # set local git config, which not affect by global config
                    self.get_command(work_tree=False) + [
                        "config", "core.autocrlf", "false" ],
                    self.get_command(work_tree=False) + [
                        "config", "core.safecrlf", "false" ],
                    self.get_command(work_tree=False) + [
                        "config", "core.symlinks", "true" ],
                    self.get_command(work_tree=False) + [
                        "config", "core.trustctime", "false" ],
                    self.get_command(work_tree=False) + [
                        "config", "core.sharedRepository", "group" ],

                    # in case of merge, use ours instead.
                    self.get_command(work_tree=False) + [
                        "config", "merge.ours.name", "\"always keep ours\" merge driver" ],
                    self.get_command(work_tree=False) + [
                        "config", "merge.ours.driver", "touch %A" ],
                   ]

        for args in commands:
            proc = subprocess.Popen( args,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT )
            communicate(proc, args)

        #log.debug("create .gitignore")
        #fp = open(os.path.join(self.root, self.WORK_TREE, ".gitignore"), "w")
        #fp.write(".gistore-*\n")
        #fp.close()


    def upgrade(self, old):
        if old < 2:
            self.upgrade_2()


    def upgrade_2(self):
        if self.GIT_DIR != ".git":
            oldgit = os.path.join(self.root, ".git")
            if os.path.exists( oldgit ):
                os.rename( oldgit, os.path.join(self.root, self.GIT_DIR) )

        commands = [ 
                    # set as bare repos
                    self.get_command(work_tree=False) + [
                            "config", "core.bare", "true" ],

                    # set local git config, which not affect by global config
                    self.get_command(work_tree=False) + [
                            "config", "core.autocrlf", "false" ],
                    self.get_command(work_tree=False) + [
                            "config", "core.safecrlf", "false" ],
                    self.get_command(work_tree=False) + [
                            "config", "core.symlinks", "true" ],
                    self.get_command(work_tree=False) + [
                            "config", "core.trustctime", "false" ],
                    self.get_command(work_tree=False) + [
                            "config", "core.sharedRepository", "group" ],

                    # in case of merge, use ours instead.
                    self.get_command(work_tree=False) + [
                            "config", "merge.ours.name", "\"always keep ours\" merge driver" ],
                    self.get_command(work_tree=False) + [
                            "config", "merge.ours.driver", "touch %A" ],
                   ]

        for args in commands:
            proc = subprocess.Popen( args,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT )
            communicate(proc, args)


    def _get_commit_count(self):
        args = self.get_command(work_tree=False) + [ "rev-list", "master" ]
        log.debug(" ".join(args))
        proc = subprocess.Popen( args,
                                 stdout=subprocess.PIPE,
                                 stderr=open('/dev/null', 'w') )
        lines = communicate( proc,
                             args,
                             exception=False,
                            )[0].splitlines()
        log.debug( "Total %d commits in master." % len(lines) )

        return len(lines)


    def backup_rotate(self):
        if not self.backup_history or self.backup_history < 1:
            return
        if not self.backup_copies or self.backup_copies < 1:
            return

        count = self._get_commit_count()
        if count <= self.backup_history:
            log.debug( "No backup rotate needed. %d <= %d." % 
                        ( count, self.backup_history ) )
            return

        log.info( "Begin backup rotate, for %d > %d." %
                    ( count, self.backup_history ) )
        # list branches with prefix: gistore/
        args = self.get_command(work_tree=False) + [ "branch" ]
        proc = subprocess.Popen( args,
                                 stdout=subprocess.PIPE,
                                 stderr=None )
        lines = sorted( communicate(proc, args)[0].splitlines() )
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
                cmd = self.get_command(work_tree=False) + [
                        "update-ref", "refs/heads/gistore/%d" % i,
                        "refs/heads/gistore/%d" %
                            tagids[ i - self.backup_copies ] ]
                command_list.append(cmd)
            for i in tagids:
                if i in range(1, self.backup_copies):
                    continue
                cmd = self.get_command(work_tree=False) + [
                        "branch", "-D", "gistore/%d" % i ]
                command_list.append(cmd)
            cmd = self.get_command(work_tree=False) + [
                    "branch", "gistore/%d" % self.backup_copies, "master" ]
            command_list.append(cmd)
        else:
            if len(tagids) > 0:
                cmd = self.get_command(work_tree=False) + [
                        "branch", "gistore/%d" % (tagids[-1] + 1), "master" ]
                tagids.append( tagids[-1] + 1 )
            else:
                cmd = self.get_command(work_tree=False) + [
                        "branch", "gistore/1", "master" ]
                tagids.append( 1 )
            command_list.append(cmd)

        for i in range(len(command_list)):
            log.debug( "Backup rotate step %d" % i )
            proc = subprocess.Popen( command_list[i],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT )
            communicate(proc, command_list[i])

        # Run: git cat-file commit master | \
        #          sed  '/^parent/ d'     | \
        #          git hash-object -t commit -w --stdin

        log.debug( "Backup rotate step %d" % (i+1) )
        cmd = self.get_command(work_tree=False) + [ "cat-file",
                                                    "commit",
                                                    "master" ]
        proc = subprocess.Popen( cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE )
        commit_contents = ''
        for line in communicate(proc, cmd)[0].splitlines():
            if not line.startswith("parent"):
                commit_contents += ( commit_contents and '\n' or '' ) + line
        
        log.debug( "commit_contents : %s" % commit_contents )
        log.debug( "Backup rotate step %d" % (i+2) )
        cmd = self.get_command(work_tree=False) + [ "hash-object",
                                                    "-t", "commit",
                                                    "-w", "--stdin" ]
        proc = subprocess.Popen( cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE )
        object_id = communicate(proc, cmd, input=commit_contents)[0].strip()

        # Run: git update-ref master object_id
        log.debug( "Backup rotate step %d" % (i+3) )
        cmd = self.get_command(work_tree=False) + [ "update-ref",
                                                    "refs/heads/master",
                                                    object_id ]
        proc = subprocess.Popen( cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE )
        communicate(proc, cmd)

        # create file .git/info/grafts.
        #   parent of object_id -> gistore/N^
        #   paretn of gistore/N last commit -> gistore/(N-1)^
        grafts = []
        id = object_id
        for i in sorted(tagids[:self.backup_copies], reverse=True):
            cmd = self.get_command(work_tree=False) + [
                                    'rev-list',
                                    'refs/heads/gistore/%d' % i ]
            proc = subprocess.Popen( cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=None )
            revlist = communicate(proc, cmd)[0].splitlines()
            grafts.append( [ id, revlist[1] ] )
            id = revlist[-1]
        f = open( os.path.join( self.root, self.GIT_DIR, 'info/grafts'), 'w' )
        for id, parent in grafts:
            f.write( "%s %s\n" % (id, parent) )
        f.close()


    def commit(self, message=None):

        # generate user friendly commit log
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
                    'detail': ", ".join( [ "%s: %d" % (k, len(status[k]))
                                        for k in sorted(status.keys()) ] ),
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
                    brief_st.append( "...%d more..." %
                                            ( len(status[k]) - sample ) )
                buffer.append( "    %s => %s" % ( k, ", ".join(brief_st) ) )

            return "\n".join(buffer)


        # add submodule as normal directory
        def add_submodule(submodule, status=[]):
            # submodule already deleted in cache

            # add tmp file in submodule
            open( os.path.join( self.root,
                                self.WORK_TREE,
                                submodule,
                                '.gistore-submodule'), 'w' ).close()

            # git add tmp file in submodule
            args = self.command + [ "add",
                                    "-f",
                                    os.path.join( submodule,
                                                  '.gistore-submodule' ) ]
            proc_add = subprocess.Popen( args,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT )
            communicate(proc_add, args)

            # git add whole submodule dir
            args = self.command + [ "add", submodule ]
            proc_add = subprocess.Popen( args,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT )
            communicate(proc_add, args)

            # git rm -f tmp file in submodule
            args = self.command + [ "rm",
                                    "-f",
                                    os.path.join( submodule,
                                                  '.gistore-submodule' ) ]
            proc_rm = subprocess.Popen( args,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT )
            communicate(proc_rm, args)

            # check status --porcelain and append to status[]
            args = self.command + [ "status", "--porcelain", submodule ]
            log.debug(" ".join(args))
            proc_st = subprocess.Popen( args,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT )
            status.extend( [ line for line in
                             communicate(proc_st, args)[0].splitlines() ] )
            return status


        ##
        self._abort_if_not_repos()

        # Check if backup needs rotate
        self.backup_rotate()

        args = self.command + [ "add", "." ]
        proc_add = subprocess.Popen( args,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT )
        communicate(proc_add, args)

        # delete files but keep directories.
        if True:
            args = self.command + [ "ls-files", "--deleted" ]
            log.debug(" ".join(args))
            proc_ls = subprocess.Popen( args,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT )
            deleted_files = []
            for file in communicate(proc_ls, args)[0].splitlines():
                deleted_files.append(file)
            if deleted_files:
                try:
                    # `git rm --cached` will not remote blank-dir.
                    args = self.get_command(work_tree=False) + \
                            [ "rm", "--cached", "--quiet" ] + \
                            deleted_files
                    proc_rm = subprocess.Popen( args,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT )
                    communicate(proc_rm, args, exception=False)
                except OSError, e:
                    if "Argument list too long" in e:
                        for file in deleted_files:
                            args = self.get_command(work_tree=False) + [
                                    "rm", "--cached", "--quiet", file ]
                            proc_rm = subprocess.Popen(
                                                args,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT )
                            communicate(proc_rm, args, exception=False)

        args = self.command + [ "status", "--porcelain" ]
        log.debug(" ".join(args))
        proc_st = subprocess.Popen( args,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT )
        commit_stat = [ line for line in communicate(proc_st, args)[0].splitlines() ]

        submodules = self.remove_submodules()
        while submodules:
            log.info( "Re-add submodules: %s", ', '.join(submodules) )
            for submod in submodules:
                commit_stat.extend( add_submodule(submod) )
            # new add directories may contain other submodule.
            submodules = self.remove_submodules()

        if message:
            message += "\n\n"
            message += commit_summary( commit_stat )
        else:
            message = commit_summary( commit_stat )

        if commit_stat:
            log.info( "Backup changes for %s\n%s" % (self.root, message) )
        else:
            log.info( "*Nothing changed*, no backup for %s\n%s" % (
                        self.root, message ) )

        msgfile = os.path.join( self.root, GISTORE_LOG_DIR, "COMMIT_MSG" )
        fp = open( msgfile, "w" )
        fp.write( message )
        fp.close()

        args = self.command + [ "commit", "--quiet", "-F", msgfile ]
        proc_ci = subprocess.Popen( args,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT )
        # If nothing to commit, git commit return 1.
        communicate( proc_ci,
                     args,
                     ignore=lambda n: n.startswith("nothing to commit")
                            or n.startswith("no changes added to commit") )


    def remove_submodules(self):
        submodules = []
        args = self.get_command(work_tree=False) + [
                    "--work-tree=.", "submodule", "status" ]
        proc = subprocess.Popen( args,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT )
        pat1 = re.compile(r".\w{40} (\w*) \(.*\)?")
        pat2 = re.compile(r"No submodule mapping found in .gitmodules for path '(.*)'")
        for line in communicate(proc, args)[0].splitlines():
            line = line.strip()
            m = pat1.match(line)
            if m:
                submodules.append(m.group(1))
            m = pat2.match(line)
            if m:
                submodules.append(m.group(1))

        if submodules:
            log.warning( "Remove submodules in backup:" + 
                         "\n    " + " ".join(submodules) )
            args = self.get_command(work_tree=False) + [
                        "rm", "--cached", "-q" ] + submodules
            proc_rm = subprocess.Popen( args,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT )
            communicate(proc_rm, args)

            # maybe other submodules
            submodules.extend( self.remove_submodules() )
            return submodules

        else:
            return []


    def log(self, args=[]):
        graft_file = os.path.join( self.root, self.GIT_DIR, 'info/grafts')
        os.putenv( "GIT_GRAFT_FILE", graft_file )
        args = self.get_command(work_tree=False) + [
                        "log" ] + args
        os.execv( args[0], args )


# vim: et ts=4 sw=4
