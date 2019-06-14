#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/DbCheck.py
#
#   Database consistency check
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

import os
import re

import chirribackup.input
import chirribackup.LocalDatabase
import chirribackup.actions.BaseAction
import chirribackup.chunk
import chirribackup.compression
import chirribackup.crypto
from chirribackup.StringFormat import dump
from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
from chirribackup.exceptions import ChirriException, ChunkBadFilenameException, ChunkNotFoundException, \
    BadParameterException


class DbCheck(chirribackup.actions.BaseAction.BaseAction):

    remote = 0
    fix = 0
    sm = None

    help = {
        "synopsis": "Check database integrity and fix problems",
        "description": [
            "This command is used to check and optionally repair the Chirri",
            "Backup local database."
        ],
        "args": [
            [ "?remote",
                "Connect to remote storage and check files."
            ],
            [ "?fix",
                "If present string option 'fix', all errors will be fixed."
            ],
            [ "?ask",
                "If present string option 'ask', user is asked before",
                "touching or breaking anything (implies 'fix')."
            ]
        ]
    }

    do_fix_always = {}


    def do_fix(self, q):
        r = self.fix != 0

        if self.fix > 1:
            if q in self.do_fix_always:
                r = True
            else:
                a = chirribackup.input.ask(q, "y", "^[yna]$")
                r = (a == "y" or a == "a")
                if a == "a":
                    self.do_fix_always[q] = 1

        if r:
            logger.info("Apply '%s'" % q)

        return r


    def check_snapshots(self):
        logger.info("check_snapshots: NOT IMPLEMENTED")
        # 1. check last id > biggest snapshot id
        # 2. check snapshots attributes
        # 2.1 check status >= 0 <= 5 or (status == -1 and rebuild)
        # 2.2 started_tstamp != NULL
        # 2.3 status > 3 => finished_tstamp != NULL
        # 2.4 status > 5 => signed_tstamp != NULL
        # 2.5 started_tstamp < finished_tstamp < signed_tstamp


    def check_refs(self):
        logger.info("check_refs: NOT IMPLEMENTED")
        # 1. all snapshots exist
        # 2. path NOT NULL
        # 3.1. hash NOT NULL OR /^[a-f0-9]+$/
        # 3.2. hash exists and size matches
        # 4. size >= 0
        # 5. status NULL OR (status >= -1 AND status <= 2)


    def check_remote_chunks(self):
        if not self.remote:
            logger.info("check_remote_chunks: check disabled -- option 'remote' not enabled")
            return

        logger.info("check_remote_chunks: started")
        logger.info("check_remote_chunks: loading list of local chunks")
        cl = {}
        for c in self.ldb.connection.execute("SELECT * FROM file_data"):
            cl[c["hash"]] = c

        logger.info("check_remote_chunks: getting list of remote chunks")
        rcl = self.sm.get_listing_chunks()

        logger.info("check_remote_chunks: parsing list of remote chunks (%d chunks)" % len(rcl))
        for f in rcl:
            cbi = chirribackup.chunk.Chunk.parse_filename(f["name"])
            if cbi["hash"] not in cl:
                logger.error("check_remote_chunks: Chunk %s does not exist in local database" % (cbi["hash"]))
            else:
                if f["size"] != cl[cbi["hash"]]["csize"]:
                    logger.error("check_remote_chunks: Chunk %s remote real size %d does not match with local size %d" \
                                    % (cbi["hash"], f["size"], cl[cbi["hash"]]["size"]))
                if cbi["size"] != cl[cbi["hash"]]["size"]:
                    logger.error("check_remote_chunks: Chunk %s remote declared size %d does not match with local size %d" \
                                    % (cbi["hash"], cbi["size"], cl[cbi["hash"]]["size"]))
                del cl[cbi["hash"]]

        logger.info("check_remote_chunks: Detecting not uploaded chunks")
        for c in cl:
            logger.error("check_remote_chunks: Chunk %s is not uploaded" % c)
            # TODO: checks depending on chunk status
            #  / pending upload
            #  / uploaded
            #  / fix not-uploaded but in theory uploaded chunk

        logger.info("check_remote_chunks: finished")


    def check_remote_snapshots(self):
        if not self.remote:
            logger.info("check_remote_snapshots: check disabled -- option 'remote' not enabled")
            return

        logger.info("check_remote_snapshots: NOT IMPLEMENTED")


    def check_chunks(self):
        logger.info("check_chunks: started")
        chunk_list = chirribackup.chunk.Chunk.list(self.ldb)
        logger.info("check_chunks: load chunk ref counters")
        chunk_ref_count = {}
        for r in self.ldb.connection.execute(
                    """
                        SELECT hash, COUNT(*) AS refcount
                        FROM file_ref
                        GROUP BY hash
                    """):
            chunk_ref_count[r["hash"]] = r["refcount"]
        logger.info("check_chunks: going to check db integrity of %d chunks" % len(chunk_list))
        i = 0
        p = 0
        for chunk in chunk_list:
            if int(i * 10 / len(chunk_list)) != p:
                p = int(i * 10 / len(chunk_list))
                logger.info("check_chunks: %d%% complete (%d chunks processed)" % (p * 10, i))

            bad_chunk = False

            # 1. check hash id
            if not chirribackup.crypto.ChirriHasher.hash_check(chunk.hash):
                logger.error("check_chunks: Malformed hash '%s' in chunk" % chunk.hash)
                bad_chunk = True

            # 2. size >= 0
            if chunk.size < 0:
                logger.error("check_chunks: Chunk '%s' with negative size" % chunk.hash_format())
                bad_chunk = True

            # 3. first_seen_as NOT NULL AND NOT VOID
            if chunk.first_seen_as is None or chunk.first_seen_as == "":
                logger.error("check_chunks: Chunk '%s' never seen with a name" % chunk.hash_format())
                bad_chunk = True

            # 4. refcount = (SELECT COUNT(*) FROM file_ref WHERE hash = hash)
            refcount = chunk_ref_count[chunk.hash] if chunk.hash in chunk_ref_count else 0

            if refcount == 0:
                logger.error("check_chunks: Chunk '%s' is never referenced", chunk.hash_format())

            if refcount != chunk.refcount:
                logger.error("check_chunks: Chunk '%s' referenced %d times, but expected %d" \
                                % (chunk.hash_format(), chunk.refcount, refcount))
                if refcount == 0:
                    # no body loves it, so is better to delete it
                    bad_chunk = True
                else:
                    # it is required by some refs... only fix counter
                    if self.do_fix("Fix ref count"):
                        self.ldb.connection.execute(
                            """
                                UPDATE file_data
                                SET refcount = :refcount
                                WHERE hash = :hash
                            """, {
                                "hash"     : chunk.hash,
                                "refcount" : refcount,
                            })
                        self.ldb.connection.commit()

            # 5. 0 <= status <= 1
            if chunk.status < 0 or chunk.status > 2:
                raise ChirriException("Not implemented")
                # i dont know what to do here

            # 6. compression algorithm
            if chunk.compression is not None and chunk.compression not in [ "lzma" ]:
                logger.error("check_chunks: Chunk %s is using unknown compression algorithm '%s'" \
                                % (chunk.hash_format(), chunk.compression))
                raise ChirriException("Not implemented")
                
            # if 'bad_chunk' flag is set, then propose to delete this chunk
            if bad_chunk and self.do_fix("Remove chunk"):
                raise ChirriException("Not implemented")
                # TODO:
                #   1) set all file_ref pointing to this to status -1
                #   2) unset this ref in all file_ref pointing to this
                #   3) if uploaded,
                #        3.1) set refcount to zero
                #      else
                #        3.2) delete this entry

            i = i + 1

        logger.info("check_chunks: finished")


    def check_local_chunks(self):
        logger.info("check_local_chunks: started")

        # get list of local chunks
        local_chunks_list = os.listdir(os.path.realpath(self.ldb.chunks_dir))
        logger.info("check_local_chunks: going to check integrity of %d local chunks" % len(local_chunks_list))

        # 1. chunks in disk are referenced by local database?
        i = 0
        p = 0
        for fname in local_chunks_list:
            if int(i * 10 / len(local_chunks_list)) != p:
                p = int(i * 10 / len(local_chunks_list))
                logger.info("check_local_chunks: %d%% complete (%d chunks processed)" % (p * 10, i))

            try:
                # set 'fpath' initially with the only date we have
                fpath = os.path.realpath(os.path.join(self.ldb.chunks_dir, fname))

                # 1.1 Good file name
                cbi = chirribackup.chunk.Chunk.parse_filename(fname)

                # 1.2 chunk not only exists in disk
                chunk = chirribackup.chunk.Chunk(self.ldb, cbi["hash"])

                # 1.3 basic information (cbi) matches with chunk info
                if chunk.size != cbi["size"] \
                or chunk.compression != cbi["compression"]:
                    raise ChirriException("cbi does not match -- Not implemented")

                # 1.4 chunk in disk but already uploaded
                if chunk.status == 2:
                    logger.error("check_local_chunks: Chunk %s already uploaded" % chunk.hash_format())
                    if self.do_fix("Delete chunk already uploaded"):
                        os.unlink(fpath)

                # set 'fpath' again, using this time the chunk() object info
                fpath = os.path.realpath(os.path.join(self.ldb.chunks_dir, chunk.get_filename()))

                # decompress and hash
                try:
                    h = chirribackup.crypto.ChirriHasher.hash_file(
                                fpath,
                                chirribackup.compression.Decompressor(chunk.compression))

                    # 1.5 chunk not uploaded, but corrupted
                    if h.nbytes != chunk.size or h.hash != chunk.hash:
                        logger.error("check_local_chunks: Chunk %s corrupted but never uploaded" % chunk.hash_format())
                        if self.do_fix("Delete chunk and set references as erroneous"):
                            os.unlink(fpath)
                            self.ldb.connection.execute(
                                    """
                                        UPDATE file_ref
                                        SET status = -1, hash = NULL
                                        WHERE hash = :hash
                                    """, { "hash" : chunk.hash })
                            self.ldb.connection.execute(
                                    "DELETE FROM file_data WHERE hash = :hash",
                                    { "hash" : chunk.hash })
                            self.ldb.connection.commit()

                except IOError, ex:
                    logger.error("check_local_chunks: Cannot read chunk %s: %s" % (fpath, ex))
                    if self.do_fix("Wat do?"):
                        raise ChirriException("Not implemented")

            except ChunkBadFilenameException, ex:
                logger.error("check_local_chunks: Bad chunk file name '%s': %s" % (fpath, ex))
                if self.do_fix("Delete file with bad chunk name"):
                    os.unlink(fpath)

            except ChunkNotFoundException, ex:
                logger.error("check_local_chunks: File hash %s does not exists in db" % fpath)
                if self.do_fix("Delete chunk not found in db"):
                    os.unlink(fpath)

            i = i + 1

        # 2. check that pending chunks are in disk
        logger.info("check_local_chunks: check pending chunks are in disk")
        for chunk in chirribackup.chunk.Chunk.list(self.ldb, status = 0) \
                   + chirribackup.chunk.Chunk.list(self.ldb, status = 1):
            fpath = os.path.realpath(os.path.join(self.ldb.chunks_dir, chunk.get_filename()))
            if not os.path.exists(fpath):
                logger.error("check_local_chunks: Not uploaded chunk %s referenced, but not found in __chunks__" \
                                % chunk.hash_format())
                if self.do_fix("Set references as erroneous"):
                    self.ldb.connection.execute(
                            """
                                UPDATE file_ref
                                SET status = -1, hash = NULL
                                WHERE hash = :hash
                            """, { "hash" : fd["hash"] })
                    self.ldb.connection.execute(
                                "DELETE FROM file_data WHERE hash = :hash",
                                { "hash" : fd["hash"] })
                    self.ldb.connection.commit()

        logger.info("check_local_chunks: finished")


    def check_db(self):
        logger.info("check_db: started")
        column_snapshots_compression_exists = False
        column_snapshots_uploaded_tstamp_exists = False
        column_snapshots_signed_tstamp_exists = False
        for c in self.ldb.connection.execute("PRAGMA table_info(snapshots)"):
            if c["name"] == "compression":
                column_snapshots_compression_exists = True
            if c["name"] == "uploaded_tstamp":
                column_snapshots_uploaded_tstamp_exists = True
            if c["name"] == "signed_tstamp":
                column_snapshots_signed_tstamp_exists = True

        # add snapshots.compression column
        if not column_snapshots_compression_exists:
            logger.warning("check_db: Adding missing column snapshots.compression")
            self.ldb.connection.execute("ALTER TABLE snapshots ADD COLUMN compression VARCHAR(8)")
            self.ldb.connection.commit()

        # add snapshots.signed column
        if not column_snapshots_signed_tstamp_exists:
            logger.warning("check_db: Adding missing column snapshots.signed_tstamp")
            self.ldb.connection.execute("ALTER TABLE snapshots ADD COLUMN signed_tstamp INTEGER")
            if column_snapshots_uploaded_tstamp_exists:
                self.ldb.connection.execute(
                    """
                        UPDATE snapshots
                        SET signed_tstamp = uploaded_tstamp
                    """)
            self.ldb.connection.commit()

        # delete snapshots.uploaded_tstamp column
        if column_snapshots_uploaded_tstamp_exists:
            # XXX: sqlite3 does not support ALTER TABLE DROP COLUMN, so we do
            # not do nothing here. It is only an unused column in a local
            # database; we can cope with some little anoying bytes.
            #logger.warning("check_db: Delete unused column snapshots.uploaded_tstamp")
            #self.ldb.connection.execute("ALTER TABLE snapshots DROP COLUMN uploaded_tstamp")
            #self.ldb.connection.commit()
            logger.warning("check_db: Detected an old database with snapshots.uploaded_tstamp column. Ignoring it.")

        # check for unknown config values
        # check status value
        rebuild = self.ldb.status < 100
        if self.ldb.status < 0 \
        or self.ldb.status > 100:
            logger.error("check_db: Unknown database status %d" % int(self.ldb.status))
            if self.do_fix("Fix database status"):
                raise ChirriException("Not implemented")

        # upgrading from db_version 1 to db_version 2
        if self.ldb.db_version == 1:
            if not self.do_fix("Upgrade database to version 2"):
                raise ChirriException("Cannot continue without upgrading database")

            # Added chunk status 1 => already choosen best compression algorithm
            #   (we move all chunks to state 2)
            self.ldb.connection.execute(
                """
                    UPDATE file_data
                    SET status = 2
                    WHERE status == 1
                """)

            # upgrade database
            self.ldb.db_version = 2
            self.ldb.connection.commit()

        logger.info("check_db: finished")


    def check_exclude(self):
        logger.info("check_exclude: started")

        for x in self.ldb.connection.execute("SELECT * FROM excludes"):
            if x["disabled"] != 0:
                continue

            if x["exclude"] == "":
                logger.error("check_exclude: Void exclude expression.")
                if self.do_fix("Delete exclude rule"):
                    self.ldb.connection.execute(
                        """
                            DELETE FROM excludes
                            WHERE exclude = :exclude_id
                        """, {
                            "exclude_id": x["exclude_id"],
                        })
                    self.ldb.connection.commit()
            elif x["expr_type"] == 2:
                try:
                    re.compile(x["exclude"])
                except re.error, ex:
                    logger.error("check_exclude: Cannot compile regex /%s/: %s" % (x["exclude"], re.error))
                    if self.do_fix("Disable exclude rule"):
                        self.ldb.connection.execute(
                            """
                                UPDATE excludes
                                SET disabled = 1
                                WHERE exclude_id = :exclude_id
                            """, {
                                "exclude_id"   : x["exclude_id"],
                            })
                        self.ldb.connection.commit()

        logger.info("check_exclude: finished")


    def parse_args(self, argv):
        fix_level = 0
        remote_check = 0
        while len(argv) > 0:
            if argv[0] == "fix":
                fix_level |= 1
                argv.pop(0)
            elif argv[0] == "ask":
                fix_level |= 2
                argv.pop(0)
            elif argv[0] == "remote":
                remote_check |= 2
                argv.pop(0)
            else:
                raise BadParameterException("Unknown flag '%s'." % argv[0])
        return {
            "fix_level" : fix_level,
            "remote_check" : remote_check,
        }


    def check_config_backups(self):
        """TODO"""
        logger.info("check_config_backups: NOT IMPLEMENTED")

    def go(self, fix_level, remote_check):
        self.fix = fix_level
        self.remote = remote_check

        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path, db_version_check = False)

        if self.remote:
            self.sm = self.ldb.get_storage_manager()

        self.check_db()
        self.check_snapshots()
        self.check_refs()
        self.check_chunks()
        self.check_local_chunks()
        self.check_remote_chunks()
        self.check_remote_snapshots()
        self.check_exclude()
        self.check_config_backups()

