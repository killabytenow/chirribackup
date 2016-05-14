#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/Actions/SnapshotDetails.py
#
#   Print details about an snapshot
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

class SnapshotDelete(ChirriBackup.Actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Delete snapshot/s",
        "description": [
            "Delete snapshot and data related to it.",
        ],
        "args": [
            [ "{snapshot_id ...}",
                "The snapshot_id (or a list of) of the selected snapshot(s)."
            ],
        ]
    }


    def go(self, args):
        if len(args) < 1:
            raise ChirriException("Need at least an snapshot id.")

        self.ldb = ChirriBackup.LocalDatabase.LocalDatabase(CONFIG.path)
        snp = ChirriBackup.Snapshot.Snapshot(self.ldb)
        while len(args) > 0:
            snp.load(args.pop(0))
            snp.delete()

