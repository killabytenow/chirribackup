#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# ChirriBackup/Actions/DbRebuild.py
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

from ChirriBackup.ChirriException import *
from ChirriBackup.Config import CONFIG
from ChirriBackup.Logger import logger
import ChirriBackup.Actions.DbCreator
import ChirriBackup.LocalDatabase
import ChirriBackup.Actions.SnapshotList
import ChirriBackup.Snapshot
import ChirriBackup.Crypto
import json
import re
import sys
import time

class DbRebuild(ChirriBackup.Actions.DbCreator.DbCreator):

    sm = None
    help = {
        "synopsis": "rebuilds a database using a remote backup",
        "description": [
            "This command is capable of rebuilding a local database using a",
            "remote backup. It connects to the remote repository, download",
            "snapshots info, rebuilds the database and restores the last",
            "succesful snapshot.  This command is designed for recovering of",
            "a catastrophe."
        ],
        "args": [
            [ "?{config_file}",
                "Optionally you can import a previously saved configuration",
                "file, which may include a complete exclude list or detailed",
                "configuration of the remote storage. By default the",
                "configuration wizard will be disabled if you provide this",
                "option. If you want to enable it, add the 'wizard' flag",
                "argument."
            ],
            [ "?wizard",
                "This optional flag can be only set if the option",
                "{config_file} is present. It enables the wizard and allows",
                "to edit the configured values in the {config_file}",
                "configuration file."
            ],
        ],
    }


    def status_0_remote_file_listing(self):
        snapshot_file_re = re.compile("^snapshots/snapshot-([1-9][0-9]*)\\.txt$")
        chunk_file_re = re.compile("^chunks/([^/]+)$")
        for f in self.sm.get_listing():
            m = snapshot_file_re.search(f["name"])
            if m is not None:
                snapshot_id = int(m.group(1))
                snp = ChirriBackup.Snapshot.Snapshot(self.ldb)
                snp.new(snapshot_id = snapshot_id)
                if snapshot_id > self.ldb.last_snapshot_id:
                    self.ldb.last_snapshot_id = snapshot_id
                snp.set_status(-1, False)
                continue

            m = chunk_file_re.search(f["name"])
            if m is None:
                logger.error("Unknown file '%s' -- ignoring it" % f["name"])
                continue

            try:
                cbi = ChirriBackup.Chunk.Chunk.parse_filename(m.group(1))
                c = ChirriBackup.Chunk.Chunk.insert(
                                self.ldb,
                                cbi["hash"],        # hash
                                cbi["size"],        # size
                                f["size"],          # csize
                                None,               # first_seen_as
                                1,                  # status 1 = uploaded
                                0,                  # refcount
                                cbi["compression"]) # compression
            except ChunkBadFilenameException, ex:
                logger.error("Bad chunk file name '%s': %s" % (f, ex))

        # commit -- now it is a good commit point
        self.ldb.status = 1
        self.ldb.connection.commit()


    def status_1_download_snapshots(self):
        for s in self.ldb.snapshot_list():
            if s.status == -1:
                data = self.sm.download_data("snapshots/snapshot-%d.txt" % s.snapshot_id)
                data = ChirriBackup.Crypto.unprotect_string(data)
                jd = json.loads(data)
                for a in [
                            "started_tstamp",
                            "finished_tstamp",
                            "uploaded_tstamp",
                         ]:
                    s.set_attribute(a, jd["details"][a])
                for fr in jd["refs"]:
                    s.file_ref_save(
                            fr["path"].encode('utf-8'),
                            fr["hash"].encode('utf-8'),
                            int(fr["size"]),
                            int(fr["perm"]),
                            int(fr["uid"]),
                            int(fr["gid"]),
                            int(fr["mtime"]),
                            int(fr["status"]))
                s.set_status(5, False)

        # commit -- now it is a good commit point
        self.ldb.status = 2
        self.ldb.connection.commit()


    def status_2_select_target_snapshot(self):
        print "Select target snapshot"
        print "======================"
        print ""
        print "Please choose which snapshot do you want to restore:"
        print ""
        ls = self.ldb.snapshot_list()
        if len(ls) > 0:
            print "  id     status  started             finished            uploaded"
            print "  ------ ------- ------------------- ------------------- -------------------"
            for ss in ls:
                if ss.deleted == 0:
                    print "  %6s %7s %19s %19s %19s" \
                        % (ss.snapshot_id,
                           ss.status,
                           time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(ss.started_tstamp)) if ss.started_tstamp is not None else None,
                           time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(ss.finished_tstamp)) if ss.finished_tstamp is not None else None,
                           time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(ss.uploaded_tstamp)) if ss.uploaded_tstamp is not None else None)

            print ""
            self.ldb.rebuild_snapshot = ChirriBackup.Input.ask(
                                            "Choose snapshot",
                                            self.ldb.last_snapshot_id,
                                            "^[1-9][0-9]*$")

        else:
            print "  THIS DATABASE DOES NOT CONTAIN ANY SNAPSHOT."
            print "  I WILL TRY TO RECOVER FILES USING THE CHUNK INFORMATION"
            print "  DIRECTLY."
            print "  PLEASE NOTE THAT THIS PROCESS IS OUR LAST BULLET"
            print "  IN A DISASTER RECOVERY AND IT MAY FAIL."
            print "  LUCK!"
            print ""
            self.ldb.rebuild_snapshot = None

        # commit -- now it is a good commit point
        self.ldb.status = 3
        self.ldb.connection.commit()


    def do_magic_recover(self):
        raise ChirriException("Not implemented.")


    def status_3_restore_files(self):
        # restore snapshot
        if self.ldb.rebuild_snapshot is not None:
            snp = ChirriBackup.Snapshot.Snapshot(self.ldb)
            snp.load(self.ldb.last_snapshot_id)
            snp.restore(self.sm, self.ldb.db_path, True)

        else:
            self.do_magic_recover()

        # everything finished -- go to normal operations state
        self.ldb.status = 100
        self.ldb.connection.commit()


    def parse_args(self, argv):
        r = {
            "config_file": None,
            "wizard": True,
        }
        if len(argv) > 0:
            r["config_file"] = argv.pop(0)
            if len(argv) > 0:
                p = argv.pop(0)
                if p == "wizard":
                    r["wizard"]
                else:
                    raise BadParameterException("Unknown flag '%s'." % p)
        return r


    def go(self, config_file, wizard):
        # default values
        config = None
        excludes = None
        wizard = True

        if config_file is not None:
            # read config file
            with open(config_file, "rb") as f:
                config_data = ChirriBackup.LocalDatabase.LocalDatabase.config_parse(f.read())
                config = {}
                for k,v in config_data["status"].iteritems():
                    config[k] = str(v["value"])
                excludes = config_data["excludes"]
        else:
            if not wizard:
                raise ChirriException("wizard must be enabled if config_file is not provided.")
            excludes = None

        # CREATE/OPEN DATABASE
        if not ChirriBackup.LocalDatabase.check_db_exists(CONFIG.path):
            # db does not exists... ask config and crete new
            if wizard:
                config = self.get_config(config)

            if config is not None:
                self.create_db(config, excludes)
            else:
                sys.exit(1)

            # create database
            self.create_db(config, excludes)

            # force status to 0 (downloading file list)
            self.ldb.status = 0
        else:
            # db already exists... open it and try to continue an interrupted
            # rebuilding process
            self.ldb = ChirriBackup.LocalDatabase.LocalDatabase(CONFIG.path, False)

        # create a storage manager
        self.sm = self.ldb.get_storage_manager()

        # do things depending on current database status
        while True:
            if self.ldb.status == 0:
                self.status_0_remote_file_listing()
            elif self.ldb.status == 1:
                self.status_1_download_snapshots()
            elif self.ldb.status == 2:
                self.status_2_select_target_snapshot()
            elif self.ldb.status == 3:
                self.status_3_restore_files()
                logger.info("Finished succesfully.")
                break
            elif self.ldb.status == 100:
                logger.info("Database is rebuilt -- please try with 'db check' instead.")
                break
            else:
                raise ChirriException("Unknown database status %d" % self.ldb.status)



