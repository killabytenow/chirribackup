#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/Crypto.py
#
#   Helper crypto funcs
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

from chirribackup.exceptions import ChirriException
import chirribackup.compression
import hashlib
import os
import re

READ_BLOCKSIZE = (1024*1024)

class ChirriHasher:
    """alias for hashlib.sha512"""
    """This is the default hasher used by Chirri Backup"""

    # ATTRIBUTES
    hasher = None
    hash   = None
    nbytes = None

    # CONSTANTS
    hash_re = re.compile("^[a-f0-9]{128}$")

    def __init__(self):
        self.hasher = hashlib.sha512()
        self.nbytes = 0
        self.hash = self.hasher.hexdigest()


    def update(self, data):
        self.hasher.update(data)
        self.nbytes = self.nbytes + len(data)
        self.hash = self.hasher.hexdigest()


    # CLASS/OBJECT METHODS
    # --------------------

    @classmethod
    def hash_check(cls, hash_ref):
        return ChirriHasher.hash_re.match(hash_ref)

    @classmethod
    def hash_format(cls, hash_ref):
        if not ChirriHasher.hash_check(hash_ref):
            raise ChirriException("Bad hash '%s'." % hash_ref)
        return hash_ref[0:10] + "..." + hash_ref[-10:]

    @classmethod
    def hash_file(cls, path, decompressor = None):
        if decompressor is None:
            decompressor = chirribackup.compression.Decompressor(None)
        h = ChirriHasher()
        with open(path, 'rb') as afile:
            buf = afile.read(READ_BLOCKSIZE)
            while len(buf) > 0:
                h.update(decompressor.decompress(buf))
                buf = afile.read(READ_BLOCKSIZE)
            h.update(decompressor.close())
        return h


def protect_header(begin):
    return "-------- %s --------" % ("HASHED CONTENT BEGINS" if begin else "HASHED CONTENT ENDS")

def protect_string(string):
    hasher = ChirriHasher()
    hasher.update(string)
    return "%s\nHash: %s\n%s\n%s\n" % (
                    protect_header(True),
                    hasher.hash,
                    string,
                    protect_header(False))


def unprotect_string(string):
    linebuffer = string.split("\n")
    hasher = ChirriHasher()

    # ignore void lines and header
    while re.compile("^\s*$").match(linebuffer[0]):
        del linebuffer[0]
    if linebuffer[0] != protect_header(True):
        raise ChirriException("Bad header.")
    del linebuffer[0]

    # fetch hash
    h = re.compile("^Hash: ([a-z0-9]+)$").search(linebuffer[0])
    if h is not None:
        h = h.group(1)
    else:
        raise ChirriException("Hash header not found.")
    del linebuffer[0]

    # calculate hash
    for i in range(0, len(linebuffer) - 1):
        if linebuffer[i] == protect_header(False):
            break
        hasher.update("\n" if i > 0 else "")
        hasher.update(linebuffer[i])
        s = "\n"

    # do check
    if linebuffer[i] != protect_header(False):
        raise ChirriException("String finished abruptly.")
    if h != hasher.hash:
        raise ChirriException("Hash does not match.")

    return "\n".join(linebuffer[0:i])
