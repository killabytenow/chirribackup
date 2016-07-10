#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/chunk.py
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

import exceptions
import os
import re
import sys

import chirribackup.compression
import chirribackup.crypto
from chirribackup.Logger import logger
from chirribackup.exceptions import \
    ChirriException,                \
    BadValueException,              \
    ChunkBadFilenameException,      \
    ChunkBadHashException,          \
    ChunkNotFoundException

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
        if not chirribackup.crypto.ChirriHasher.hash_check(hash):
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


    def new(self, source_file):
        # local_file (source_file in ldb.db_path)
        local_file = os.path.join(self.ldb.db_path, source_file)
        tmp_file = os.path.join(self.ldb.chunks_dir, "tmp.%s" % os.getpid())

        # hash target file
        sh = chirribackup.crypto.ChirriHasher()
        try:
            with open(local_file, 'rb') as ifile:
                buf = ifile.read(READ_BLOCKSIZE)
                while len(buf) > 0:
                    sh.update(buf)
                    buf = ifile.read(READ_BLOCKSIZE)

        except exceptions.IOError, ex:
            raise ChirriException("Cannot hash file '%s': %s" % (source_file, ex))

        # set basic attribs
        self.hash          = sh.hash
        self.size          = sh.nbytes
        self.csize         = None
        self.first_seen_as = source_file
        self.status        = 0
        self.refcount      = 0
        self.compression   = None

        # configure target_file path
        target_file = os.path.join(self.ldb.chunks_dir, self.get_filename())

        # check if this chunk exists already in local database
        oc = self.ldb.connection.execute(
                    "SELECT * FROM file_data WHERE hash = :hashkey",
                    { "hashkey" : sh.hash }).fetchone()
        if oc is not None:
            # check the improbability
            if sh.nbytes != oc["size"]:
                raise ChirriException("OMG! File '%s' matches with chunk %s, but it differs in size."
                                        % (target_file, self.hash_format()))

            # hash already processed, load and return
            logger.debug("Chunk %s already exists for file %s" \
                                % (self.hash_format(), source_file))
            return self.load(sh.hash)

        # if the target_file already exists (was generated, but not reg in db),
        # delete it
        if os.path.exists(target_file):
            logger.warning("A local chunk '%s' was already created -- deleting it." \
                            % self.hash_format())
            os.unlink(target_file)

        # create the file snapshot 'target_file' (without compression)
        compressor = chirribackup.compression.Compressor(None, tmp_file)
        sh = chirribackup.crypto.ChirriHasher()
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

        # check hash and update csize
        if sh.hash != self.hash or sh.nbytes != self.size:
            raise ChunkChangedException("Chunk %s changed during snapshot" % source_file)
        if sh.nbytes != compressor.bytes_out:
            raise ChirriException(
                    "Null compressor bytes %d do not match with hash bytes %d" \
                        % (compressor.bytes_out, sh.nbytes))
        self.csize = compressor.bytes_out

        # commit target_file and register chunk in database
        os.rename(tmp_file, target_file)
        self.ldb.connection.execute(
                """
                    INSERT INTO file_data
                        (hash, size, csize, first_seen_as, status, refcount, compression)
                        VALUES (:hash, :size, :csize, :path, :status, 0, :compression)
                """, {
                    "hash"        : self.hash,
                    "size"        : self.size,
                    "csize"       : self.csize,
                    "path"        : self.first_seen_as,
                    "status"      : self.status,
                    "compression" : self.compression,
                })

        return self


    def compress(self, compression):
        # sanity checks
        if self.status != 0:
            raise ChirriException(
                    "Chunk cannot be compressed in status %d" % self.status)

        # trivial case => user do not want compression
        if compression is None \
        or compression == self.compression:
            # leave chunk in the current state (probably uncompressed)
            logger.debug("%s: %s, not applying compression %s." \
                % (self.get_filename(),
                   ("Compressed with " + self.compression) \
                       if self.compression is not None else "Uncompressed",
                   "NONE" if compression is None else compression))
            return False

        # get paths
        old_chunk_file = os.path.join(self.ldb.chunks_dir, self.get_filename())
        tmp_file = os.path.join(self.ldb.chunks_dir, "tmp.%s" % os.getpid())

        # try compressing it using 'compression' algorithm
        # NOTE: we must decompress the existing chunk using the current
        #       compression algorithm (probably None)
        decompressor = chirribackup.compression.Decompressor(self.compression)
        compressor = chirribackup.compression.Compressor(compression, tmp_file)
        sh = chirribackup.crypto.ChirriHasher()
        try:
            # read, write & hash
            with open(old_chunk_file, 'rb') as ifile:
                # read first block
                buf = ifile.read(READ_BLOCKSIZE)
                while len(buf) > 0:
                    # decompress data
                    buf = decompressor.decompress(buf)

                    # compress data & hash
                    compressor.compress(buf)
                    sh.update(buf)

                    # read more data
                    buf = ifile.read(READ_BLOCKSIZE)

                # last pending bytes
                buf = decompressor.close()
                compressor.compress(buf)
                sh.update(buf)
                compressor.close()

        except exceptions.IOError, ex:
            os.unlink(tmp_file)
            raise ChirriException("Cannot recompress chunk %s: %s" \
                                    % (self.hash_format(), ex))

        # check hashes
        if sh.hash != self.hash:
            os.unlink(tmp_file)
            raise ChirriException(
                    "Data in file '%s' does not match with chunk %s" \
                        % (sh.hash, self.hash))

        # check if compression has worked
        if compressor.bytes_out >= self.csize:
            if self.csize == 0:
                logger.warning("Found zero bytes chunk '%s'." % self.hash_format())
            else:
                logger.warning("Storing '%s' uncompressed (uncompressed=%d < %s=%d; ratio %.2f)" \
                            % (self.hash_format(),
                               self.csize,
                               compression, compressor.bytes_out,
                               float(compressor.bytes_out) / float(self.csize)))
            os.unlink(tmp_file)
            sys.exit(1)
            return False

        # ok .. proceed to update chunk with compressed version
        # update chunk info
        logger.debug("Chunk %s compressed (%d < %d)" \
                % (self.hash_format(), compressor.bytes_out, self.csize))
        self.compression = compression
        self.csize = compressor.bytes_out
        self.ldb.connection.execute(
            """
                UPDATE file_data
                SET compression = :compression, csize = :csize
                WHERE hash = :hash
            """, {
                "compression" : self.compression,
                "csize"       : self.csize,
                "hash"        : self.hash,
            })

        # calculate new file name
        new_chunk_file = os.path.join(self.ldb.chunks_dir, self.get_filename())

        # rename tmp_file
        if os.path.exists(new_chunk_file):
            logger.warning("A local chunk '%s' was already created -- deleting it." \
                            % self.hash_format())
            os.unlink(new_chunk_file)
        os.rename(tmp_file, new_chunk_file)
        self.ldb.connection.commit()
        os.unlink(old_chunk_file)

        return True



    def download(self, sm, target_file, overwrite = False):
        remote_chunk = "chunks/%s" % self.get_filename()
        tmp_file = target_file + ".download"

        # if file exists, try
        if os.path.exists(target_file):
            # overwrite check
            if not overwrite:
                raise ChirriException("Chunk file '%s' already exists." % target_file)

            # yep! chunk is already on disk.. decide what to do...
            eh = chirribackup.crypto.hash_file(target_file)
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
                decompressor = chirribackup.compression.Decompressor(self.compression, target_file)
                sh = chirribackup.crypto.ChirriHasher()
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
        if value < 0 or value > 2:
            raise BadValueException("Bad chunk status value %s" % value)
        self.status = value;
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
        return chirribackup.crypto.ChirriHasher.hash_format(self.hash)


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
                                  % chirribackup.crypto.ChirriHasher.hash_format(hash))

        return Chunk(ldb, hash)


