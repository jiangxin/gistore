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
from gistore.errors import *

class AbstractSCM(object):

    WORK_TREE = "."

    def __init__(self, root="", backup_history=0, backup_copies=0):
        self.set_root(root)
        self.backup_history = backup_history
        self.backup_copies  = backup_copies

    def set_root(self, root=""):
        if not root:
            root = os.getcwd()
        self.root = os.path.realpath(root)
        
    def _abort_if_not_repos(self):
        if not self.is_repos():
            raise UninitializedRepositoryError

    def is_repos(self):
        raise NoImplementError("not implement is_repos")

    def init(self):
        raise NoImplementError("not implement init")

    def commit(self):
        raise NoImplementError("not implement commit")

    def post_check(self):
        return

