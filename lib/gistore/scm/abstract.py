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

    def __init__(self, root=""):
        self.set_root(root)

    def set_root(self, root=""):
        if not root:
            root = os.getcwd()
        self.root = os.path.realpath(root)
        
    def _abort_if_not_repos(self):
        if not self.is_repos():
            raise UninitializedRepositoryError

    def is_repos(self):
        raise NoImplementError

    def init(self):
        raise NoImplementError

    def commit(self):
        raise NoImplementError

    def post_check(self):
        return

