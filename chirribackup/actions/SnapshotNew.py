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

from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
from chirribackup.exceptions import ChirriException, UnknownParameterException
import chirribackup.LocalDatabase
import chirribackup.actions.BaseAction
import chirribackup.input
import chirribackup.snapshot
import re
import sys

class SnapshotNew(chirribackup.actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Creates a new snapshot",
        "description": [
            "This action creates a new snapshot database and configures it."
        ],
        "args": [
            [ "?({base_snapshot_id}|inc|incremental)",
                "A snapshot_id for using as base snapshot (incremental",
                "backup). If keywords 'inc' or 'incremental', the last",
                "snapshot_id will be used as base snapshot",
            ]
        ]
    }


    def parse_args(self, argv):
        r = {}

        if len(argv) > 0:
            r["base_snapshot_id"] = argv.pop(0)
            if r["base_snapshot_id"].lower() == "inc" \
            or r["base_snapshot_id"].lower() == "incremental":
                r["base_snapshot_id"] = "incremental"
            elif re.compile("^([1-9][0-9]*|0)$").match(r["base_snapshot_id"]):
                r["base_snapshot_id"] = int(r["base_snapshot_id"])
            else:
                raise UnknownParameterException("Bad base_snapshot_id '%s'." % r["base_snapshot_id"])

        return r


    def go(self, base_snapshot_id = None):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)

        if base_snapshot_id is not None:
            if base_snapshot_id == "incremental":
                # load last snapshot and get its id
                base_snapshot_id = chirribackup.snapshot.Snapshot(self.ldb).load().snapshot_id
            else:
                base_snapshot_id = int(base_snapshot_id)
            logger.info("Creating incremental snapshot based on %d" % base_snapshot_id)
        else:
            logger.info("Creating new snapshot from scratch")

        snp = chirribackup.snapshot.Snapshot(self.ldb)
        snp.new(base_snapshot_id)
        snp.run()


