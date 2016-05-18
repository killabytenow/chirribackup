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

from chirribackup.exceptions import *
from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
import chirribackup.actions.BaseAction
import chirribackup.Crypto
import chirribackup.Input
import chirribackup.LocalDatabase
import os
import re
import sys


class DbCheck(chirribackup.actions.BaseAction.BaseAction):

    fix = 0

    help = {
        "synopsis": "Check database integrity and fix problems",
        "description": [
            "This command is used to check and optionally repair the Chirri",
            "Backup local database."
        ],
        "args": [
            [ "?fix",
                "If present string option 'fix', all errors will be fixed."
            ],
            [ "?ask",
                "If present string option 'ask', user is asked before",
                "touching or breaking anything (implies 'fix')."
            ]
        ]
    }


    def do_fix(self, q):
        r = self.fix != 0

        if self.fix > 1:
            r = (chirribackup.Input.ask(q, "y", "^[yn]$") == "y")

        if r:
            logger.info("Apply '%s'" % q)

        return r


    def check_snapshots(self):
        logger.info("Checking snapshots...")
        # 1. check last id > biggest snapshot id
        # 2. check snapshots attributes
        # 2.1 check status >= 0 <= 5 or (status == -1 and rebuild)
        # 2.2 started_tstamp != NULL
        # 2.3 status > 3 => finished_tstamp != NULL
        # 2.4 status > 5 => uploaded_tstamp != NULL
        # 2.5 started_tstamp < finished_tstamp < uploaded_tstamp


    def check_refs(self):
        logger.info("Checking file references...")
        # 1. all snapshots exist
        # 2. path NOT NULL
        # 3.1. hash NOT NULL OR /^[a-f0-9]+$/
        # 3.2. hash exists and size matches
        # 4. size >= 0
        # 5. status NULL OR (status >= -1 AND status <= 2)


    def check_chunks(self):
        logger.info("Checking chunks...")
        for chunk in chirribackup.Chunk.Chunk.list(self.ldb):
            bad_chunk = False

            # 1. check hash id
            if not chirribackup.Crypto.ChirriHasher.hash_check(chunk.hash):
                logger.error("Malformed hash '%s' in chunk" % chunk.hash)
                bad_chunk = True

            # 2. size >= 0
            if chunk.size < 0:
                logger.error("Chunk '%s' with negative size" % chunk.hash_format())
                bad_chunk = True

            # 3. first_seen_as NOT NULL AND NOT VOID
            if chunk.first_seen_as is None or chunk.first_seen_as == "":
                logger.error("Chunk '%s' never seen with a name" % chunk.hash_format())
                bad_chunk = True

            # 4. refcount = (SELECT COUNT(*) FROM file_ref WHERE hash = hash)
            refcount = self.ldb.connection.execute(
                            """
                                SELECT COUNT(*) AS refcount
                                FROM file_ref
                                WHERE hash = :hash
                            """, {
                                "hash" : chunk.hash,
                            }).fetchone()["refcount"]
            if refcount != chunk.refcount:
                logger.error("Chunk '%s' referenced %d times, but expected %d" \
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
            if chunk.status < 0 or chunk.status > 1:
                raise ChirriException("Not implemented.")
                # i dont know what to do here

            # 6. compression algorithm
            if chunk.compression is not None and chunk.compression not in [ "lzma" ]:
                logger.error("Chunk %s is using unknown compression algorithm '%s'." \
                                % (chunk.hash_format(), chunk.compression))
                raise ChirriException("Not implemented.")
                
            # if 'bad_chunk' flag is set, then propose to delete this chunk
            if bad_chunk and self.do_fix("Remove chunk"):
                raise ChirriException("Not implemented.")
                # TODO:
                #   1) set all file_ref pointing to this to status -1
                #   2) unset this ref in all file_ref pointing to this
                #   3) if uploaded,
                #        3.1) set refcount to zero
                #      else
                #        3.2) delete this entry


    def check_local_chunks(self):
        logger.info("Checking local chunks...")

        # 1. chunks in disk are referenced by local database?
        for fname in os.listdir(os.path.realpath(self.ldb.chunks_dir)):
            try:
                # 1.1 Good file name
                cbi = chirribackup.Chunk.Chunk.parse_filename(fname)

                # 1.2 chunk not only exists in disk
                chunk = chirribackup.Chunk.Chunk(self.ldb, cbi["hash"])

                # 1.3 basic information (cbi) matches with chunk info
                if chunk.size != cbi["size"] \
                or chunk.compression != cbi["compression"]:
                    raise ChirriException("cbi does not match -- Not implemented.")

                # 1.4 chunk in disk but already uploaded
                if chunk.status == 1:
                    logger.error("Chunk %s already uploaded." % chunk.hash_format())
                    if self.do_fix("Delete chunk"):
                        os.unlink(fpath)

                # decompress and hash
                fpath = os.path.realpath(os.path.join(self.ldb.chunks_dir, chunk.get_filename()))
                try:
                    h = chirribackup.Crypto.ChirriHasher.hash_file(
                                fpath,
                                chirribackup.Compression.Decompressor(chunk.compression))

                    # 1.5 chunk not uploaded, but corrupted
                    if h.nbytes != chunk.size or h.hash != chunk.hash:
                        logger.error("Chunk %s corrupted but never uploaded" % chunk.hash_format())
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

                except exceptions.IOError, ex:
                    logger.error("Cannot read chunk %s: %s" % (fpath, ex))
                    if self.do_fix("Wat do?"):
                        raise ChirriException("Not implemented.")

            except ChunkBadFilenameException, ex:
                logger.error("Bad chunk file name '%s': %s" % (fname, ex))
                if self.do_fix("Delete file"):
                    os.unlink(fpath)

            except ChunkNotFoundException, ex:
                logger.error("File hash %s does not exists in db" % chunk.hash_format())
                if self.do_fix("Delete chunk"):
                    os.unlink(fpath)

        # 2. check that pending chunks are in disk
        for chunk in chirribackup.Chunk.Chunk.list(self.ldb, status = 0):
            fpath = os.path.realpath(os.path.join(self.ldb.chunks_dir, chunk.get_filename()))
            if not os.path.exists(fpath):
                logger.error("Not uploaded chunk %s referenced, but not found in __chunks__" \
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


    def check_db(self):
        # add snapshot compression column
        column_compression_exists = False
        for c in self.ldb.connection.execute("PRAGMA table_info(snapshots)"):
            if c["name"] == "compression":
                column_compression_exists = True
        if not column_compression_exists:
            logger.warning("Adding missing column snapshots.compression")
            self.ldb.connection.execute("ALTER TABLE snapshots ADD COLUMN compression VARCHAR(8)")
        self.ldb.connection.commit()

        # check for unknown config values
        # check status value
        rebuild = self.ldb.status < 100
        if self.ldb.status < 0 \
        or self.ldb.status > 100:
            logger.error("Unknown database status %d." % int(self.ldb.status))
            if self.do_fix("Fix status"):
                raise ChirriException("Not implemented.")


    def check_exclude(self):
        for x in self.ldb.connection.execute("SELECT * FROM excludes"):
            if x["disabled"] != 0:
                continue

            if x["exclude"] == "":
                logger.error("Void exclude expression.")
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
                    logger.error("Cannot compile regex /%s/: %s" % (x["exclude"], re.error))
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


    def parse_args(self, argv):
        fix_level = 0
        while len(argv) > 0:
            if argv[0] == "fix":
                fix_level |= 1
                argv.pop(0)
            elif argv[0] == "ask":
                fix_level |= 2
                argv.pop(0)
            else:
                raise BadParameterException("Unknown flag '%s'." % argv[0])
        return {
            "fix_level" : fix_level,
        }


    def check_config_backups(self):
        """TODO"""

    def go(self, fix_level):
        self.fix = fix_level

        self.ldb = chirribackup.LocalDatabase.LocalDatabase(CONFIG.path)

        self.check_db()
        self.check_snapshots()
        self.check_refs()
        self.check_chunks()
        self.check_local_chunks()
        self.check_exclude()
        self.check_config_backups()

