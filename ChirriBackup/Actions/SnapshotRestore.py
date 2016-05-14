#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/Actions/SnapshotRestore.py
#
#   Downloads and restore an snapshot
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

from ChirriBackup.ChirriException import ChirriException
from ChirriBackup.Config import CONFIG
from ChirriBackup.Logger import logger
import ChirriBackup.Actions.BaseAction
import ChirriBackup.LocalDatabase
import ChirriBackup.Snapshot
import sys

class SnapshotRestore(ChirriBackup.Actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Downloads and restore an snapshot",
        "description": [
            "Downloads an snapshot to a certain local directory.",
        ],
        "args": [
            [ "{snapshot_id}",
                "The snapshot_id of the selected snapshot."
            ],
            [ "{target_dir}",
                "The selected local directory.",
            ],
            [ "?overwrite",
                "If this flag is present, data found in {target_dir} will",
                "be overwritten."
            ],
        ]
    }

 
    def go(self, args):
        overwrite = False

        if len(args) < 2:
            raise ChirriException("Need an snapshot id and a local directory path.")
        elif len(args) == 3:
            if args[2] == "overwrite":
                overwrite = True
            else:
                raise ChirriException("Unknown parameter '%s'." % args[2])
        elif len(args) > 3:
            raise ChirriException("Too many parameters.")

        self.ldb = ChirriBackup.LocalDatabase.LocalDatabase(CONFIG.path)
        snp = ChirriBackup.Snapshot.Snapshot(self.ldb)
        snp.load(args[0])
        snp.restore(self.ldb.get_storage_manager(), args[1], overwrite)

