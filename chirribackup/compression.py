#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/compression.py
#
#   Helper compression funcs
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

from chirribackup.exceptions import BadCompressionException
from chirribackup.Logger import logger
import json

lzma_available = False
try:
    import lzma
    lzma_available = True
except ImportError, e:
    logger.warning("lzma import not available.")

def algorithm_check(algorithm):
    return (algorithm is None or algorithm in [ "lzma" ])

class Compressor:

    algorithm   = None
    target_file = None
    compressor  = None
    bytes_in    = None
    bytes_out   = None

    def __init__(self, algorithm, target_file = None):
        self.algorithm = algorithm
        self.bytes_in  = 0
        self.bytes_out = 0
        if self.algorithm is None:
            self.compressor = None
        elif self.algorithm == "lzma":
            if not lzma_available:
                raise BadCompressionException("LZMA (xz) compressor not available.")
            self.compressor = lzma.LZMACompressor()
        else:
            raise BadCompressionException("Uknown compression algorithm '%s'." % self.algorithm)

        self.out_file = open(target_file, "wb") \
                            if target_file is not None else None


    def compress(self, data):
        self.bytes_in = len(data)
        if self.algorithm == "lzma":
            data = self.compressor.compress(data)
        if self.out_file is not None:
            self.out_file.write(data)
        self.bytes_out += len(data)
        return data


    def close(self):
        if self.algorithm == "lzma":
            data = self.compressor.flush()
        else:
            data = ""
        if self.out_file is not None:
            if len(data) > 0:
                self.out_file.write(data)
            self.out_file.close()
        self.compressor = None
        self.out_file = None
        self.bytes_out += len(data)
        return data


class Decompressor:

    algorithm    = None
    target_file  = None
    decompressor = None
    bytes_in     = None
    bytes_out    = None

    def __init__(self, algorithm, target_file = None):
        self.algorithm = algorithm
        self.bytes_in  = 0
        self.bytes_out = 0
        if self.algorithm is None:
            self.decompressor = None
        elif self.algorithm == "lzma":
            if not lzma_available:
                raise BadCompressionException("LZMA (xz) decompressor not available.")
            self.decompressor = lzma.LZMADecompressor()
        else:
            raise BadCompressionException("Uknown compression algorithm '%s'." % self.algorithm)

        self.out_file = open(target_file, "wb") \
                            if target_file is not None else None


    def decompress(self, data):
        if self.algorithm == "lzma":
            data = self.decompressor.decompress(data)
        if self.out_file is not None:
            self.out_file.write(data)
        return data


    def close(self):
        data = ""
        if self.algorithm == "lzma":
            #if not self.decompressor.eof():
            #    raise BadCompressionException("Unfinished lzma stream.")
            data = self.decompressor.flush()
        if self.out_file is not None:
            self.out_file.write(data)
            self.out_file.close()
        self.decompressor = None
        self.out_file = None
        return data


