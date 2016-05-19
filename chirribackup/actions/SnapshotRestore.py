#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/SnapshotRestore.py
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

from chirribackup.exceptions import ChirriException, UnknownParameterException
from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
import chirribackup.actions.BaseAction
import chirribackup.LocalDatabase
import chirribackup.Snapshot
import sys

class SnapshotRestore(chirribackup.actions.BaseAction.BaseAction):

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

 
    def parse_args(self, argv):
        r = {}
        r["snapshot_id"] = int(argv.pop(0))
        r["target_dir"] = argv.pop(0)
        if len(argv) > 0:
            p = argv.pop(0)
            if p == "overwrite":
                r["overwrite"] = True
            else:
                raise UnknownParameterException("Unknown parameter '%s'." % p)
        return r


    def go(self, snapshot_id, target_dir, overwrite = False):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        chirribackup.Snapshot.Snapshot(self.ldb) \
                .load(snapshot_id) \
                .restore(self.ldb.get_storage_manager(), target_dir, overwrite)


