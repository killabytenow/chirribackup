#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/SnapshotPrint.py
#
#   Print snapshot json
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
import chirribackup.LocalDatabase
import chirribackup.Snapshot
import sys
import time

class SnapshotPrint(chirribackup.actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Print snapshot json description",
        "description": None,
        "args": [
            [ "?(json,txt)",
                "This parameter decides output format (default txt).",
            ],
            [ "{snapshot_id}",
                "The snapshot_id of the selected snapshot.",
            ]
        ]
    }


    def parse_args(self, argv):
        r = {}
        if len(argv) > 1:
            of = argv.pop(0)
            if of == "json":
                r["output_format"] = "json"
            elif of == "txt" or of == "text":
                r["output_format"] = "txt"
            else:
                raise UnknownParameterException("Unknown parameter '%s'." % of)
        r["snapshot_id"] = int(argv.pop(0))
        
        return r


    def go(self, snapshot_id, output_format = "txt"):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        snp = chirribackup.Snapshot.Snapshot(self.ldb).load(snapshot_id)
        print snp.desc_print(output_format)


