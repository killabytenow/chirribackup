#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/DbStatus.py
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

from chirribackup.exceptions import ChirriException
from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
from chirribackup.StringFormat import format_num_bytes
import chirribackup.actions.BaseAction
import chirribackup.LocalDatabase
import chirribackup.input
import sys

class DbStatus(chirribackup.actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Prints info about the database",
        "description": None,
        "args": None,
    }
 

    def parse_args(self, argv):
        return {}


    def go(self):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)
        counters = self.ldb.counters()

        print "Local database status:"

        if int(self.ldb.status) < 100:
            print "  - Database is being rebuilt!"
        print "  - %d chunks in repository" % counters["chunks"]
        print "      - %d are not referenced" % counters["chunks_not_referenced"]
        print "      - %d are uploaded" % counters["chunks_uploaded"]
        print "      - %d are not uploaded" % counters["chunks_not_uploaded"]
        if counters["excludes"] > 0:
            print "  - %d exclude rules (see exclude list)" % counters["excludes"]
        if counters["chunks_bytes"] is None:
            print "  - No data stored yet"
        else:
            print "  - %s stored" % format_num_bytes(counters["chunks_bytes"])
            print "      - %s not referenced" % format_num_bytes(counters["chunks_bytes_not_referenced"])
            print "      - %s compressed data (ratio %.2f)" % (
                                format_num_bytes(counters["chunks_compressed_bytes"]),
                                counters["compression_ratio"])
            print "      - %s uploaded" % format_num_bytes(counters["chunks_compressed_bytes_uploaded"])
            for c,t in counters["compression"].items():
                print "            %s: %s => %s (ratio %.2f)" % (
                            c,
                            format_num_bytes(t["size"]),
                            format_num_bytes(t["csize"]),
                            t["ratio"]
                        )
            print "      - %s pending upload (estimated size %s)" % (
                            format_num_bytes(counters["chunks_bytes_pending_upload"]),
                            format_num_bytes(
                                counters["chunks_bytes_pending_upload"] \
                                * counters["compression_ratio"]))
        print "  - %d snapshots in database" % (counters["snapshots"])

        if counters["snapshots"] > 0:
            print "  - Snapshots:"
            for s, fr in counters["file_refs"].items():
                print "        snapshot(%d) = %d files" % (s, fr)

        # print config
        print "  - config:"
        config = self.ldb.config_attrib_list()
        max_length = max([len(x) for x in config.iterkeys()])
        for k, v in sorted(config.items()):
            print ("        %-" + str(max_length) + "s = %s") \
                    % (k, "\"%s\"" % v["value"] if v["type"] == "str" else v["value"])

