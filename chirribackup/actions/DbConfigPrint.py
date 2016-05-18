#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/DbConfigPrint.py
#
#   Prints stored config
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


class DbConfigPrint(chirribackup.actions.BaseAction.BaseAction):

    fix = 0
    rebuild = 0

    help = {
        "synopsis": "Print an stored configuration",
        "description": [
            "This command prints an stored config (see {config_id} or prints",
            "the current running config (if {config_id} is not specified).",
        ],
        "args": [
            [ "?config_id",
                "Id of the stored config selected."
            ]
        ]
    }


    def parse_args(self, argv):
        r = {}
        if len(argv) > 0:
            r["config_id"] = argv.pop(0)
        return r


    def go(self, config_id = None):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)

        if config_id is not None:
            c = self.ldb.config_get(config_id)
        else:
            c = self.ldb.config_snapshot()

        print json.dumps(c,
                        sort_keys  = True,
                        indent     = 4,
                        separators = (',', ': '))


