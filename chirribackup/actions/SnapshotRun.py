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
import chirribackup.Snapshot
import sys

class SnapshotRun(chirribackup.actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Starts or continues an interrupted snapshot",
        "description": [
            "This action starts a snapshot or continues an interrupted",
            "snapshot.",
        ],
        "args": [
            [ "{snapshot_id}",
                "The snapshot_id of the snapshot selected."
            ]
        ]
    }
 

    def parse_args(self, argv):
        return {
            "snapshot_id": int(argv.pop(0)),
        }


    def go(self, snapshot_id):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        chirribackup.Snapshot.Snapshot(self.ldb) \
            .load(snapshot_id) \
            .run()


