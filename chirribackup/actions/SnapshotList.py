#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/SnapshotList.py
#
#   List snapshots
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
import chirribackup.Input
import sys
import time

class SnapshotList(chirribackup.actions.BaseAction.BaseAction):

    help = {
        "synopsis": "List snapshots",
        "description": [
            "List available snapshots and their statuses.",
        ],
        "args": None,
    }


    def parse_args(self, argv):
        return {}


    def go(self):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        print "snapshot  status  deleted started             finished            uploaded            compression"
        print "--------- ------- ------- ------------------- ------------------- ------------------- -----------"
        for ss in self.ldb.snapshot_list():
            print "%9s %7s %7s %19s %19s %19s %11s" \
                % (ss.snapshot_id,
                   ss.status,
                   "deleted" if ss.deleted != 0 else "",
                   time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(ss.started_tstamp)) if ss.started_tstamp is not None else None,
                   time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(ss.finished_tstamp)) if ss.finished_tstamp is not None else None,
                   time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(ss.uploaded_tstamp)) if ss.uploaded_tstamp is not None else None,
                   ss.compression)


