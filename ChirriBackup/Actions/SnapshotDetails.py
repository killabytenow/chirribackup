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

class SnapshotDetails(ChirriBackup.Actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Give detailed info about an snapshot",
        "description": [
            "Print some detailed info about an snapshot and list",
            "contents related to it in database.",
        ],
        "args": [
            [ "{snapshot_id}",
                "The snapshot_id of the selected snapshot.",
            ]
        ]
    }


    def go(self, args):
        if len(args) != 1:
            raise ChirriException("Need an snapshot id.")

        self.ldb = ChirriBackup.LocalDatabase.LocalDatabase(CONFIG.path)
        snp = ChirriBackup.Snapshot.Snapshot(self.ldb)
        snp.load(args[0])

        print "Details for snapshot %d" % (snp.snapshot_id)
        print "    status             = %s" % (snp.status if snp.status is not None else "")
        print "    started timestamp  = %s" % (snp.started_tstamp if snp.started_tstamp is not None else "not started")
        print "    finished timestamp = %s" % (snp.finished_tstamp if snp.finished_tstamp is not None else "not finished")
        print ""
        print "Files:"
        print ""

        f = [ 23, 10, 10, 6, 4, 4, 14, 6, 30 ]
        print ("%" + ("s %".join("-{0}".format(n) for n in f)) + "s") % (
                    "hash",
                    "size",
                    "%deflate",
                    "perm",
                    "uid",
                    "gid",
                    "mtime",
                    "status",
                    "path")
        l = [ ]
        for i in f:
            l.append("-" * i)
        print " ".join(l)
        for ref in snp.refs():
            print ("%" + ("s %".join("-{0}".format(n) for n in f)) + "s") % (
                    snp.file_ref_format(ref["hash"]),
                    ref["size"],
                    "%s(%.1f)" \
                        % (ref["compression"],
                           (float(ref["csize"]) / float(ref["size"]))) \
                        if ref["csize"] is not None \
                        and ref["compression"] is not None else "none",
                    "%o" % ref["perm"],
                    ref["uid"],
                    ref["gid"],
                    ref["mtime"],
                    ref["status"],
                    ref["path"])

