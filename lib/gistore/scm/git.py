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

from subprocess import Popen, PIPE, STDOUT
import os

from gistore.scm.abstract import AbstractSCM
from gistore.utils import *
from gistore.config import *

class SCM(AbstractSCM):

    def is_repos(self):
        return os.path.exists( os.path.join(self.root, '.git', 'objects') )

    def init(self):
        if self.is_repos():
            verbose("Repos %s already exists." % self.root, LOG_WARNING)
            return False
        cmdline = "git init"
        args = ["git", "init", self.root]
        proc = Popen(args, stdout=PIPE, stderr=STDOUT, close_fds=True)
        exception_if_error(proc, cmdline)
        fp = open(os.path.join(self.root, ".gitignore"), "w")
        fp.write(GISTORE_CONFIG_DIR)
        fp.write("\n")
        fp.close()

    def commit(self, message="no message"):
        self._abort_if_not_repos()
        os.chdir(self.root)
        args = ["git", "add", "."]
        cmdline = "git add ."
        verbose(cmdline, LOG_DEBUG)
        proc_add = Popen(args, stdout=PIPE, stderr=STDOUT, close_fds=True)
        exception_if_error(proc_add, cmdline)

        args = ["git", "ls-files", "--deleted"]
        verbose("git ls-files --deleted.", LOG_DEBUG)
        proc_ls = Popen(args, stdout=PIPE, stderr=STDOUT, close_fds=True)
        for file in proc_ls.stdout.readlines():
            # strip last CRLF
            file = file.rstrip()
            if not os.path.isdir(file):
                # git removes directories when the last file
                # in them is removed, but empty directories
                # may be significant. Touch a flag file to
                # prevent git from removing the directory.
                flagfile=""
                if os.path.exists(os.path.dirname(file)) and not os.listdir(os.path.dirname(file)):
                    flagfile=os.path.join(os.path.dirname(file), ".gistore-keep-empty")
                    os.mknod(flagfile, 0644)
                cmdline = "git rm --quiet %s" % file
                args = ["git", "rm", "--quiet", file]
                proc_rm = Popen(args, stdout=PIPE, stderr=STDOUT, close_fds=True)
                warn_if_error(proc_rm, cmdline)
                if flagfile:
                    os.unlink(flagfile)

        username = os.getenv("SUDO_USER")
        if username:
            import socket
            os.putenv("GIT_COMMITTER_NAME", username)
            os.putenv("GIT_COMMITTER_EMAIL", username+"@"+socket.gethostname())

        cmdline = "git commit -m %s" % message
        verbose(cmdline, LOG_DEBUG)
        args = ["git", "commit", "--quiet", "-m", message]
        proc_ci = Popen(args, stdout=PIPE, stderr=STDOUT, close_fds=True)
        # If nothing to commit, git commit return 1.
        exception_if_error2(proc_ci, cmdline, test=lambda n: n.startswith("nothing to commit"))

