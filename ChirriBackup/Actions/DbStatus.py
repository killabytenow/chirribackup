#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/Actions/DbStatus.py
#
#   Get info
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
import ChirriBackup.Input
import sys

class DbStatus(ChirriBackup.Actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Prints info about the database",
        "description": None,
        "args": None,
    }
 
    def go(self, args):
        self.ldb = ChirriBackup.LocalDatabase.LocalDatabase(CONFIG.path)
        counters = self.ldb.counters()

        print "Local database status:"

        if int(self.ldb.status) < 100:
            print "  - Database is being rebuilt!"
        print "  - %d blobs in repository, %d are unused" % (counters["blobs"], counters["hangers"])
        if counters["excludes"] > 0:
            print "  - %d exclude rules (see exclude list)" % counters["excludes"]
        if counters["blob_bytes"] is None:
            print "  - No data stored yet"
        elif counters["blob_bytes"] > (1024.0*1024.0*1024.0):
            print "  - %.2f Gb stored" % (counters["blob_bytes"] / (1024.0*1024.0*1024.0))
        elif counters["blob_bytes"] > (1024.0*1024.0):
            print "  - %.2f Mb stored" % (counters["blob_bytes"] / (1024.0*1024.0))
        elif counters["blob_bytes"] > 1024.0:
            print "  - %.2f Kb stored" % (counters["blob_bytes"] / 1024.0)
        else:
            print "  - %.2f bytes stored" % counters["blob_bytes"]
        print "  - %d snapshots in database" % (counters["snapshots"])

        if counters["snapshots"] > 0:
            print "  - Snapshots:"
            for s, fr in counters["file_refs"].items():
                print "        snapshot(%d) = %d files" % (s, fr)

        # print config
        print "  - config:"
        config = self.ldb.get()
        max_length = max([len(x) for x in config.iterkeys()])
        for k, v in sorted(config.items()):
            print ("        %-" + str(max_length) + "s = '%s'") % (k, v["value"])

