#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/Syncer.py
#
#   Syncs database and uploads&delete chunks and snapshots
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
import json
import os
import time
import traceback

import chirribackup.Snapshot
import chirribackup.compression
from chirribackup.Logger import logger
from chirribackup.exceptions import ChirriException, ChunkNotFoundException, ChunkBadFilenameException

class Syncer(object):

    ldb = None
    sm  = None
    counters = None

    def __init__(self, ldb):
        self.ldb = ldb
        self.sm = self.ldb.get_storage_manager()
        self.counters = {
            "bytes"           : 0,
            "files"           : 0,
            "snapshots"       : 0,
            "chunks"          : 0,
        }

    def sync_snapshots(self):
        logger.info("Syncing snapshots")
        for snp in self.ldb.snapshot_list():
            if snp.deleted:
                if snp.status == 5:
                    # uploaded snapshot marked for deletion
                    #   => delete remote snapshot
                    logger.info("[DEL] Remote snapshot %d" % snp.snapshot_id)
                    target_file = "snapshots/snapshot-%d.txt" % snp.snapshot_id
                    if snp.compression is not None:
                        target_file += "." + snp.compression
                    self.sm.delete_file(target_file)
                else:
                    logger.info("[DEL] Local snapshot %d" % snp.snapshot_id)

                # now snapshot is only local, and still marked for deletion
                #   => destroy snapshot
                #   => update file_data.refcount
                snp.destroy()

            else:
                if snp.status == 4:
                    # prepare snapshot for upload
                    snp.set_attribute("uploaded_tstamp", int(time.time()))
                    desc = snp.desc_print()
                    if snp.compression is None:
                        if self.ldb.compression is not None:
                            c = chirribackup.compression.Compressor(self.ldb.compression)
                            zdesc = c.compress(desc)
                            zdesc += c.close()
                            if len(zdesc) < len(desc):
                                snp.set_attribute("compression", self.ldb.compression)
                                desc = zdesc
                    else:
                        c = chirribackup.compression.Compressor(snp.compression)
                        desc = c.compress(desc)
                        desc += c.close()

                    # upload!
                    self.sm.upload_data("snapshots/%s" % snp.get_filename(), desc)
                    snp.set_status(5)
                    logger.info("[UPD] Snapshot %d" % snp.snapshot_id)

                    # update counters
                    self.counters["bytes"]     += len(desc)
                    self.counters["snapshots"] += 1
                    self.counters["files"]     += 1

            # commit on each operation
            self.ldb.connection.commit()


    def sync_chunks(self):
        logger.info("Syncing chunks")
        for chunk in chirribackup.Chunk.Chunk.list(self.ldb):
            local_chunk = os.path.realpath(os.path.join(self.ldb.chunks_dir, chunk.get_filename()))
            remote_chunk = "chunks/%s" % chunk.get_filename()

            if chunk.status == 0:
                # not uploaded chunk...
                if chunk.refcount > 0:
                    # referenced chunk, not uploaded => upload
                    try:
                        self.sm.upload_file(remote_chunk, local_chunk)
                        chunk.set_status(1)
                        # NOTE: this commit is important: sets file as uploaded, then
                        # after the local chunk may be unlinked.
                        self.ldb.connection.commit()
                        os.unlink(local_chunk)
                        self.counters["bytes"]  += chunk.size
                        self.counters["chunks"] += 1
                        self.counters["files"]  += 1
                        logger.info("[UPD] %s" % chunk.hash_format())
                    except ChirriException, e:
                        logger.error("Error uploading chunk %s based on %s" \
                                        % (self.ldb.hash_format(chunk.hash), chunk.first_seen_as))
                        logger.error(traceback.format_exc(), escape_nl = False)
                        raise
                else:
                    # not referenced chunk, not uploaded => local delete
                    logger.info("[LDL] Deleting pending chunk %s" % chunk.hash_format())
                    os.unlink(local_chunk)
                    chunk.destroy()
            elif chunk.refcount == 0:
                # uploaded chunk not referenced => delete from server
                logger.warning("[DEL] Remote chunk %s." % chunk.hash_format())
                self.sm.delete_file(remote_chunk)
                chunk.destroy()

            # commit on each operation
            self.ldb.connection.commit()

        # delete forgotten chunks in disk
        for fname in os.listdir(os.path.realpath(self.ldb.chunks_dir)):
            try:
                cbi = chirribackup.Chunk.Chunk.parse_filename(fname)
                c = chirribackup.Chunk.Chunk(self.ldb, cbi["hash"])

                if c.status == 1:
                    # this local chunk should not exist
                    logger.warning("[LDL] Unlinking forgotten local chunk %s." % c.hash_format())
                    os.unlink(os.path.join(self.ldb.chunks_dir, c.get_filename()))

            except ChunkNotFoundException, ex:
                logger.warning("Unreferenced and unknown chunk %s found." \
                                % os.path.join(self.ldb.chunks_dir, c.hash_format()))

            except ChunkBadFilenameException, ex:
                logger.error("Bad chunk file name '%s': %s" % (fname, ex))


    def sync_config_backups(self):
        logger.info("Syncing config backups")
        for c in self.ldb.config_get():
            if c["status"] == 0:
                if c["deleted"]:
                    self.ldb.config_destroy(c["config_id"])
                else:
                    self.sm.upload_data(
                        "configs/config-%d.txt" % c["config_id"],
                        json.dumps(c["config"]))
            else:
                if c["deleted"]:
                    self.sm.delete_file("configs/config-%d.txt" % c["config_id"])
                    self.ldb.config_destroy(c["config_id"])


    def run(self):
        # upload snapshots
        self.sync_snapshots()

        # upload chunks pending of previous cancelled uploads
        self.sync_chunks()

        # upload chunks pending of previous cancelled uploads
        self.sync_config_backups()

        # Wait until pending operations complete
        # NOTE: please note that the storage manager may be asynchronous
        self.sm.complete()


