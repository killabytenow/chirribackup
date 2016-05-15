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

class SnapshotDiff(ChirriBackup.Actions.BaseAction.BaseAction):

    help = {
        "synopsis": "Diff between snapshots",
        "description": [
            "Diff two snapshots.",
        ],
        "args": [
            [ "{snapshot_a_id}",
                "The snapshot id's of the first snapshot.",
            ],
            [ "{snapshot_b_id}",
                "The snapshot id's of the second snapshot.",
            ],
        ]
    }


    def k(self, r):
        return "%s-%s-%d-%d-%d-%d-%d" % (
                    r["path"],
                    r["hash"],
                    r["size"],
                    r["perm"],
                    r["uid"],
                    r["gid"],
                    r["mtime"])


    def parse_args(self, argv):
        return {
            "snapshot_id": argv.pop(0),
        }


    def go(self, snapshot_a_id, snapshot_b_id):
        self.ldb = ChirriBackup.LocalDatabase.LocalDatabase(CONFIG.path)

        # load snapshots
        a = ChirriBackup.Snapshot.Snapshot(self.ldb, snapshot_a_id)
        b = ChirriBackup.Snapshot.Snapshot(self.ldb, snapshot_b_id)

        if a.status < 4:
            raise ChirriException("Snapshot A is not finished. At least status 4 is needed.")
        if b.status < 4:
            raise ChirriException("Snapshot A is not finished. At least status 4 is needed.")

        # iterate references
        d = { }
        for n, s in { 1 : a, 2 : b }.iteritems():
            for r in s.refs():
                if not r["path"] in d:
                    d[r["path"]] =  { "where" : 0, "a_k" : "", "b_k" : "" }
                d[r["path"]]["a_k" if n == 1 else "b_k"] = self.k(r)
                d[r["path"]]["where"] = d[r["path"]]["where"] | n

        # remove dups
        for k, p in d.items():
            if p["where"] == 3 and p["a_k"] == p["b_k"]:
                del d[k]

        # print diff
        if len(d) == 0:
            print "No differences."
        else:
            for k, p in d.iteritems():
                print "%01x [%s][%s]" % (p["where"], p["a_k"], p["b_k"])


