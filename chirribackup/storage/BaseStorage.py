#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/storage/BaseStorage.py
#
#   Abstract base backup storage plugin
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

def GetStorageManager(backend, ldb, config = False):
    if backend is None:
        raise ChirriException("None storage manager")

    modref = __import__("chirribackup.storage.%s" % backend,
                fromlist=["chirribackup.storage"])
    if modref is None:
        raise ChirriException("Uknown storage manager chirribackup.storage.%s" % backend)
    classref = getattr(modref, backend)
    return classref(ldb, config)


class BaseStorage(object):

    # class attributes
    name = None
    storage_status_keys = {}

    # object attributes
    ldb = None

    def __init__(self, ldb, config = False):
        self.ldb = ldb


    def ask_config(self, config):
        """this method is used during configuration by actions.DbCreator"""
        raise ChirriException("This method must be overrided")

    def path_join(self, a, *p):
        path = a
        for b in p:
            if b.startswith('/'):
                path = b
            elif path == '' or path.endswith('/'):
                path +=  b
            else:
                path += '/' + b
        return path

    def upload_file(self, remote_file, local_path):
        """upload a file"""
        raise ChirriException("This method must be overrided")

    def upload_data(self, remote_file, data):
        """post a file"""
        raise ChirriException("This method must be overrided")

    def inventory(self, callback = None):
        """get existing files in local storage"""
        raise ChirriException("This method must be overrided")

    def download_file(self, remote_file, local_path, callback = None):
        """download a file to disk"""
        raise ChirriException("This method must be overrided")

    def download_data(self, remote_file, callback = None):
        """get file contents"""
        raise ChirriException("This method must be overrided")

    def delete_file(self, remote_file):
        """delete file"""
        raise ChirriException("This method must be overrided")

    def complete(self):
        """complete asynchronous operations"""

