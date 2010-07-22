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

class NoImplementError(Exception):
    pass

class CommandError(Exception):
    pass

class UninitializedRepositoryError(Exception):
    pass

class PemissionDeniedError(Exception):
    pass

class TaskNotExistsError(Exception):
    """Task directory does not exists."""

class TaskAlreadyExistsError(Exception):
    """Task directory already exists."""

class GistoreLockError(Exception):
    """Lock failed."""
