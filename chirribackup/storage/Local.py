#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/storage/Local.py
#
#   Local backup storage -- backup is organized in a local folder
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
from chirribackup.Logger import logger
import chirribackup.Input
import chirribackup.storage.BaseStorage
import shutil
import os
import stat

class DirectoryNotFoundLocalStorageException(ChirriException):
    """Exception launched when directory is not found"""

class NotDirectoryLocalStorageException(ChirriException):
    """Exception launched when directory is not found"""


class Local(chirribackup.storage.BaseStorage.BaseStorage):

    # class attributes
    name = "Local storage"
    storage_status_keys = {
        "sm_local_storage_dir": { "save": 1, "type": "str", "value": None },
    }

    # object attributes
    ls_path = None

    def __init__(self, ldb, config = False):
        super(Local, self).__init__(ldb, config)
        if not config:
            self.ls_path = os.path.realpath(self.ldb.sm_local_storage_dir)
            if not os.path.isdir(self.ls_path):
                os.makedirs(self.ls_path, 0770)


    def __build_ls_path(self, remote_file, create_dir = False):
        if isinstance(remote_file, list):
            remote_file = os.path.join(*remote_file)
        target_file = os.path.realpath(os.path.join(self.ls_path, remote_file))

        if not target_file.startswith(os.path.join(self.ls_path, "")) \
        and target_file != self.ls_path:
            raise ChirriException("Target file '%s' outside of localstorage dir '%s'." % (remote_file, self.ls_path))

        target_dir = os.path.dirname(target_file)
        if not os.path.exists(target_dir):
            if create_dir:
                os.makedirs(target_dir, 0770)
            else:
                raise DirectoryNotFoundLocalStorageException("Directory %s not found." % target_dir)
        elif not os.path.isdir(target_dir):
                raise NotDirectoryLocalStorageException("%s is not a directory." % target_dir)

        return target_file


    def ask_config(self, config):
        ok = False
        while not ok:
            config["sm_local_storage_dir"] = os.path.realpath(chirribackup.Input.ask("storage directory", config["sm_local_storage_dir"]))
            if os.path.exists(config["sm_local_storage_dir"]) \
            and not os.path.isdir(config["sm_local_storage_dir"]):
                logger.error("Path '%s' is not a directory.")
            else:
                ok = True


    def upload_file(self, remote_file, local_file):
        """upload a file"""
        target_file = self.__build_ls_path(remote_file, True)
        shutil.copyfile(local_file, target_file)


    def upload_data(self, remote_file, data):
        """post a file"""
        target_file = self.__build_ls_path(remote_file, True)
        with open(target_file, "wb", 0660) as ofile:
            ofile.write(data)


    def get_listing(self, path = ""):
        l = []
        try:
            for f in os.listdir(self.__build_ls_path(path)):
                if os.path.isdir(self.__build_ls_path([ path, f ])):
                    l.extend(self.get_listing(self.path_join(path, f)))
                else:
                    statinfo = os.lstat(self.__build_ls_path([ path, f ]))
                    l.append({
                        "name" : self.path_join(path, f),
                        "size" : statinfo.st_size,
                    })
        except DirectoryNotFoundLocalStorageException, ex:
            logger.warning("No snapshots found.")

        return l


    def download_file(self, remote_file, local_path):
        """download a file to disk"""
        shutil.copyfile(self.__build_ls_path(remote_file, False), local_path)

    def download_data(self, remote_file):
        with open(self.__build_ls_path(remote_file, False), "r") as f:
            data = f.read()
        return data

    def delete_file(self, remote_file):
        os.unlink(self.__build_ls_path(remote_file, False))


