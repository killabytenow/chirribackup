#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/ExcludeList.py
#
#   List exclude rules
#
# -----------------------------------------------------------------------------
# Chirri Backup - Cheap and ugly backup tool
#   Copyright (C) 2016 Gerardo Garcia Peña <killabytenow@gmail.com>
#
#   This program is free software; you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the Free
#   Software Foundation, either version 3 of the License, or (at your option)
#   any later version.
#
#   This program is distributed in the hope that it will be useful, but WITHOUT
#   ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#   FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
#   more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program. If not, see <http://www.gnu.org/licenses/>.
# 
###############################################################################

from chirribackup.exceptions import ChirriException
from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
import chirribackup.actions.BaseAction
import chirribackup.Exclude
import chirribackup.LocalDatabase
import os
import sys

class ExcludeList(chirribackup.actions.BaseAction.BaseAction):

    fix = 0
    rebuild = 0

    help = {
        "synopsis": "List exclude rules",
        "description": None,
        "args": None,
    }
 

    def parse_args(self, argv):
        return {}


    def go(self):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        print "id   disabled type     ignore_case expression"
        print "---- -------- -------- ----------- --------------------------------------------------"
        for x in chirribackup.Exclude.Exclude.list(self.ldb):
            print "%4d %-8s %-8s %-11s %s" \
                % (x.exclude_id,
                   "disabled" if x.disabled != 0 else "",
                   x.expr_type,
                   "yes" if x.ignore_case != 0 else "no",
                   x.exclude)

