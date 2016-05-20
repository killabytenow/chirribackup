#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/Init.py
#
#   Initialize database and initialize basic parameters
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
import chirribackup.LocalDatabase
import chirribackup.snapshot
import chirribackup.Input
import sys
import re

class SnapshotNew(chirribackup.actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Creates a new snapshot",
        "description": [
            "This action creates a new snapshot database and configures it."
        ],
        "args": [
            [ "?{base_snapshot_id}",
                "A snapshot_id for using as base snapshot (inc backup).",
            ]
        ]
    }


    def parse_args(self, argv):
        r = {}
        if len(argv) > 0:
            r["base_snapshot_id"] = int(argv.pop(0))
        return r


    def go(self, base_snapshot_id = None):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)

        if base_snapshot_id is not None:
            logger.info("Creating incremental snapshot based on %d" % base_snapshot_id)
        else:
            logger.info("Creating new snapshot from scratch")

        snp = chirribackup.snapshot.Snapshot(self.ldb)
        snp.new(base_snapshot_id)
        snp.run()


