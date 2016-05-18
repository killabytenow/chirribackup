#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/DbConfigList.py
#
#   Print a list of saved configurations
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

from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
import chirribackup.actions.BaseAction
import chirribackup.Crypto
import chirribackup.Input
import chirribackup.LocalDatabase
import os
import json
import sys
import time


class DbConfigList(chirribackup.actions.BaseAction.BaseAction):

    fix = 0
    rebuild = 0

    help = {
        "synopsis": "Print the list of saved configurations",
        "description": None,
        "args": None,
    }


    def parse_args(self, argv):
        return {}


    def go(self):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        print "config_id status  tstamp              deleted"
        print "--------- ------- ------------------- -------"
        for c in self.ldb.config_get():
            print "%9s %7s %19s %s" \
                % (c["config_id"],
                   c["status"],
                   time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(c["tstamp"])) if c["tstamp"] is not None else None,
                   "deleted" if c["deleted"] != 0 else "")

