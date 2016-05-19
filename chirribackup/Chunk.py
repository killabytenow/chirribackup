#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/Chunk.py
#
#   Represents a chunk (in disk and database)
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
from __future__ import absolute_import

from chirribackup.Logger import logger
from chirribackup.exceptions import \
    ChirriException,                \
    BadValueException,              \
    ChunkBadFilenameException,      \
    ChunkBadHashException,          \
    ChunkNotFoundException
import chirribackup.Compression
import chirribackup.Crypto
import exceptions
import os
import re

# CONSTANTS
READ_BLOCKSIZE = (1024*1024)

# CHUNK CLASS
class Chunk(object):

    ldb           = None
    hash          = None
    size          = None
    csize         = None
    first_seen_as = None
    status        = None
    refcount      = None
    compression   = None

    def __init__(self, ldb, hash = None):
        self.ldb = ldb
        if hash is not None:
            self.load(hash)


    def load(self, hash):
        if not chirribackup.Crypto.ChirriHasher.hash_check(hash):
            raise ChunkBadHashException("Bad hash '%s'." % hash)
        c = self.ldb.connection.execute(
                "SELECT * FROM file_data WHERE hash = :hash",
                { "hash" : hash }).fetchone()
        if c is None:
            raise ChunkNotFoundException("Chunk '%s' does not exist." % hash)
        self.hash          = c["hash"]
        self.size          = c["size"]
        self.csize         = c["csize"]
        self.first_seen_as = c["first_seen_as"]
        self.status        = c["status"]
        self.refcount      = c["refcount"]
        self.compression   = c["compression"]
        return self


    def new(self, source_file, compression):
        # local_file (source_file in ldb.db_path)
        local_file = os.path.join(self.ldb.db_path, source_file)
        tmp_file = os.path.join(self.ldb.chunks_dir, "tmp.%s" % os.getpid())

        # create snapshot (while hashing and compressing)
        compressor = chirribackup.Compression.Compressor(compression, tmp_file)
        sh = chirribackup.Crypto.ChirriHasher()
        try:
            with open(local_file, 'rb') as ifile:
                buf = ifile.read(READ_BLOCKSIZE)
                while len(buf) > 0:
                    compressor.compress(buf)
                    sh.update(buf)
                    buf = ifile.read(READ_BLOCKSIZE)
                compressor.close()

        except exceptions.IOError, ex:
            os.unlink(tmp_file)
            raise ChirriException("Cannot hash & copy file '%s': %s" % (source_file, ex))

        if compressor.bytes_out > sh.nbytes:
            # omg ... compressed data is bigger than uncompressed
            # rollback and copy file
            if sh.nbytes == 0:
                logger.warning("Found zero bytes file '%s'." % source_file)
            else:
                logger.warning("Storing '%s' uncompressed (uncompressed=%d < %s=%d; ratio %.2f)" \
                            % (source_file,
                               sh.nbytes,
                               compression, compressor.bytes_out,
                               float(compressor.bytes_out) / float(sh.nbytes)))
            os.unlink(tmp_file)
            return self.new(source_file, None)

        # set basic attribs
        self.hash          = sh.hash
        self.size          = sh.nbytes
        self.csize         = compressor.bytes_out
        self.first_seen_as = source_file
        self.status        = 0
        self.refcount      = 0
        self.compression   = compression

        # configure target_file path
        target_file = os.path.join(self.ldb.chunks_dir, self.get_filename())

        # check if this chunk exists already in local database
        oc = self.ldb.connection.execute(
                    "SELECT * FROM file_data WHERE hash = :hashkey",
                    { "hashkey" : sh.hash }).fetchone()
        if oc is not None:
            # remove the tmp_file ... we dont need it anymore
            os.unlink(tmp_file)

            # check the improbability
            if sh.nbytes != oc["size"]:
                raise ChirriException("OMG! File '%s' matches with chunk %s, but it differs in size."
                                        % (target_file, self.hash_format()))

            # hash already processed, load and return
            return self.load(sh.hash)

        # commit the target_file
        if os.path.exists(target_file):
            try:
                # hash found file
                decompressor = chirribackup.Compression.Decompressor(compression)
                eh = chirribackup.Crypto.ChirriHasher()
                with open(target_file, 'rb') as ifile:
                    buf = ifile.read(READ_BLOCKSIZE)
                    while len(buf) > 0:
                        eh.update(decompressor.decompress(buf))
                        buf = ifile.read(READ_BLOCKSIZE)
                    eh.update(decompressor.close())

                if sh.hash != eh.hash:
                    logger.warning("Target file '%s' exists but differs of '%s' -- deleting target" \
                                            % (target_file, source_file))
                    os.unlink(target_file)
                    os.rename(tmp_file, target_file)
                else:
                    # check the improbability
                    if sh.nbytes != eh.nbytes:
                        raise ChirriException("OMG! Target file '%s' exists, with same hash of '%s', but differs in size." \
                                                % (target_file, source_file))
                    logger.warning("Local chunk '%s' already exists." % self.hash_format())
                    # use the existing chunk snapshot -- it is already there
                    os.unlink(tmp_file)
            except exceptions.IOError, ex:
                logger.warning("Target file '%s', and cannot read: %s" \
                                    % (target_file, ex))
                os.unlink(target_file)
        else:
                os.rename(tmp_file, target_file)

        # okay... now register chunk in database
        self.ldb.connection.execute(
                """
                    INSERT INTO file_data
                        (hash, size, csize, first_seen_as, status, refcount, compression)
                        VALUES (:hash, :size, :csize, :path, 0, 0, :compression)
                """, {
                    "hash"        : self.hash,
                    "size"        : self.size,
                    "csize"       : self.csize,
                    "path"        : self.first_seen_as,
                    "compression" : self.compression,
                })

        return self


    def download(self, sm, target_file, overwrite = False):
        remote_chunk = "chunks/%s" % self.get_filename()
        tmp_file = target_file + ".download"

        # if file exists, try
        if os.path.exists(target_file):
            # overwrite check
            if not overwrite:
                raise ChirriException("Chunk file '%s' already exists." % target_file)

            # yep! chunk is already on disk.. decide what to do...
            eh = chirribackup.Crypto.hash_file(target_file)
            if eh.hash != h:
                # hashes doesn't match... it is surely an old partial chunk of
                # a previous restore operation (cancelled), delete it from disk
                logger.warning("Old tmp download '%s' found but corrupt. Reloading again.")
                os.unlink(target_file)
            else:
                # hashes match, so it is the file that we need -- continue as
                # usual without downloading anything
                logger.info("Found previous temp download '%s' with matching hash. Recycling it.")
                return

        # ok... download raw chunk
        sm.download_file(remote_chunk, tmp_file)

        # decompress it
        if self.compression is None:
            os.rename(tmp_file, target_file)
        else:
            try:
                decompressor = chirribackup.Compression.Decompressor(self.compression, target_file)
                sh = chirribackup.Crypto.ChirriHasher()
                with open(tmp_file, 'rb') as ifile:
                    buf = ifile.read(READ_BLOCKSIZE)
                    while len(buf) > 0:
                        sh.update(decompressor.decompress(buf))
                        buf = ifile.read(READ_BLOCKSIZE)
                    sh.update(decompressor.close())

                if sh.hash != self.hash:
                    raise ChirriException("Bad data recovered (%s, %s)" \
                                            % (target_file, self.first_seen_as))

            except exceptions.IOError, ex:
                os.unlink(target_file)
                raise ChirriException("Cannot hash & copy file '%s': %s" % (source_file, ex))
            finally:
                os.unlink(tmp_file)


    def __refcount_sum(self, value):
            self.ldb.connection.execute(
                """
                    UPDATE file_data
                    SET refcount = refcount + :value
                    WHERE hash = :hash
                """, {
                    "value" : value,
                    "hash"  : self.hash,
                })
            c = self.ldb.connection.execute(
                "SELECT refcount FROM file_data WHERE hash = :hash",
                { "hash"  : self.hash }).fetchone()
            if c is None:
                raise ChirriException("Chunk %s does not exists." % self.hash_format())
            c = c[0]
            if c < 0:
                raise ChirriException("Negative ref in chunk %s." % self.hash_format())
            return c


    def refcount_inc(self):
        return self.__refcount_sum(1)


    def refcount_dec(self):
        return self.__refcount_sum(-1)


    def set_status(self, value):
        if value < 0 or value > 1:
            raise BadValueException("Bad chunk status value %s" % value)
        self.ldb.connection.execute(
            """
                UPDATE file_data
                SET status = :value
                WHERE hash = :hash
            """, {
                "hash"  : self.hash,
                "value" : value,
            })


    def hash_format(self):
        return chirribackup.Crypto.ChirriHasher.hash_format(self.hash)


    def get_filename(self, prefix = "", postfix = ""):
        return Chunk.compose_filename(self.hash, self.size, self.compression, prefix, postfix)


    @classmethod
    def parse_filename(cls, fname):
        m = re.compile("^([a-f0-9]+)((\.[a-zA-Z0-9_]+)+)$").match(fname)
        if m is None:
            raise ChunkBadFilenameException("Bad chunk file name '%s'." % fname)

        hash = m.group(1)
        if len(m.group(2)) == 0:
            raise ChunkBadFilenameException("Expected extensions in '%s'" % fname)

        exts = m.group(2)[1:]
        exts = exts.split(".")

        if len(exts) == 0:
            raise ChunkBadFilenameException("Expected chunk size in '%s'" % fname)
        size = exts.pop(0)

        if len(exts) > 0:
            compression = exts.pop(0)
        else:
            compression = None

        if len(exts) > 0:
            raise ChunkBadFilenameException("Too many extensions in chunk '%s'" % fname)
        return {
            "hash"        : hash,
            "size"        : int(size),
            "compression" : compression,
        }


    @classmethod
    def compose_filename(cls, hash, size, compression, prefix = "", postfix = ""):
        r = "%s.%d" % (hash, size)
        if compression is not None:
            r = r + "." + compression
        r = "%s%s%s" % (prefix, r, postfix)
        return r


    @classmethod
    def list(cls, ldb, status = None, refcount = None):
        l = []
        wl = []
        if status is not None:
            wl.append("status = :status")
        if refcount is not None:
            wl.append("refcount <= :refcount")
        select = "SELECT hash FROM file_data"
        if len(wl) > 0:
            select = select + " WHERE " + " AND ".join(wl)
        for row in ldb.connection.execute(
                        select,
                        {
                            "status"   : status,
                            "refcount" : refcount,
                        }):
            l.append(Chunk(ldb, row["hash"]))
        return l


    @classmethod
    def insert(cls, ldb, hash, size, csize, first_seen_as, status, refcount, compression):
        # insert in database
        oc = ldb.connection.execute(
                    "SELECT * FROM file_data WHERE hash = :hash",
                    { "hash" : hash }).fetchone()
        if oc is None:
            # insert new hash
            ldb.connection.execute(
                    """
                        INSERT INTO file_data
                            (hash, size, csize, first_seen_as, status, refcount, compression)
                            VALUES (:hash, :size, :csize, :first_seen_as, :status, :refcount, :compression)
                    """, {
                        "hash"          : hash,
                        "size"          : size,
                        "csize"         : csize,
                        "first_seen_as" : first_seen_as,
                        "status"        : status,
                        "refcount"      : refcount,
                        "compression"   : compression,
                    })
        else:
            raise ChirriException("Cannot add existing chunk %s" \
                                  % chirribackup.Crypto.ChirriHasher.hash_format(hash))

        return Chunk(ldb, hash)


