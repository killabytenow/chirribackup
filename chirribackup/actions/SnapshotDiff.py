#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/SnapshotDetails.py
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

from chirribackup.ChirriException import ChirriException
from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
import chirribackup.actions.BaseAction
import chirribackup.LocalDatabase
import chirribackup.Snapshot
import sys
import time

class SnapshotDiff(chirribackup.actions.BaseAction.BaseAction):

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
            "snapshot_a_id": int(argv.pop(0)),
            "snapshot_b_id": int(argv.pop(0)),
        }


    def go(self, snapshot_a_id, snapshot_b_id):
        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)

        # load snapshots
        a = chirribackup.Snapshot.Snapshot(self.ldb).load(snapshot_a_id)
        b = chirribackup.Snapshot.Snapshot(self.ldb).load(snapshot_b_id)

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
                d[r["path"]]["a" if n == 1 else "b"] = r
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
            # print header
            f = [ 3, 8, 4, 4, 4, 8, 19, 40 ]
            print ("%" + ("s %".join("-{0}".format(n) for n in f)) + "s") % (
                        "st",
                        "content",
                        "perm",
                        "uid",
                        "gid",
                        "size",
                        "mtime",
                        "path")
            l = [ ]
            for i in f:
                l.append("-" * i)
            print " ".join(l)

            # print diff's
            for k, p in d.iteritems():
                if p["where"] != 3:
                    s = "a" if p["where"] == 1 else "b"
                    print ("%" + ("s %".join("-{0}".format(n) for n in f)) + "s") \
                            % ("del" if p["where"] == 0x1 else "new",
                               "",
                               "%o" % p[s]["perm"],
                               p[s]["uid"],
                               p[s]["gid"],
                               p[s]["size"],
                               time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(p[s]["mtime"])) \
                                   if p[s]["mtime"] is not None else None,
                               p[s]["path"])
                else:
                    print ("%" + ("s %".join("-{0}".format(n) for n in f)) + "s") \
                            % ("chg",
                               "",
                               "%o" % p["a"]["perm"],
                               p["a"]["uid"],
                               p["a"]["gid"],
                               p["a"]["size"],
                               time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(p["a"]["mtime"])) \
                                   if p["a"]["mtime"] is not None else None,
                               p["a"]["path"])
                    print ("%" + ("s %".join("-{0}".format(n) for n in f)) + "s") \
                            % ("...",
                               "yes" if p["a"]["hash"] != p["b"]["hash"] else "",
                               "%o" % p["b"]["perm"] if p["a"]["perm"] != p["b"]["perm"] else "\"",
                               p["b"]["uid"]         if p["a"]["uid"]  != p["b"]["uid"]  else "\"",
                               p["b"]["gid"]         if p["a"]["gid"]  != p["b"]["gid"]  else "\"",
                               p["b"]["size"]        if p["a"]["size"] != p["b"]["size"] else "\"",
                               (time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(p["b"]["mtime"])) \
                                   if p["b"]["mtime"] is not None else None) \
                                    if p["a"]["mtime"] != p["b"]["mtime"] else "\"",
                               p["a"]["path"])


