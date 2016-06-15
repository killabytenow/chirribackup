#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/storage/GoogleStorage.py
#
#   Google storage (Standard, Durable Reduced Availability, Nearline) backup
#   storage: backups are stored in the Google Cloud Platform, using the Google
#   storage API.
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

import StringIO
import base64
import errno
import hashlib
import json
import os
import socket

from googleapiclient import discovery
from googleapiclient import errors
from googleapiclient import http
from oauth2client.service_account import ServiceAccountCredentials

from chirribackup.Logger import logger
from chirribackup.StringFormat import format_num_bytes
from chirribackup.exceptions import ChirriException, \
                                    StorageTemporaryCommunicationException
import chirribackup.input
import chirribackup.storage.BaseStorage


class GoogleStorage(chirribackup.storage.BaseStorage.BaseStorage):

    # class attributes
    name = "Google Cloud storage"
    storage_status_keys = {
        "sm_gs_json_creds_file": { "save": 1, "type": "str", "value": None },
        "sm_gs_bucket":          { "save": 1, "type": "str", "value": None },
        "sm_gs_folder":          { "save": 1, "type": "str", "value": None },
    }

    # object attributes
    scopes = None
    credentials = None
    service = None

    def __init__(self, ldb, config = False):
        super(GoogleStorage, self).__init__(ldb, config)
        if not config:
            # okay .. not in config (ask_config() method)
            # load credentials and authenticate
            self.scopes = ['https://www.googleapis.com/auth/devstorage.read_write']
            self.credentials = ServiceAccountCredentials.from_json_keyfile_name(
                                    self.ldb.sm_gs_json_creds_file,
                                    scopes=self.scopes)
            self.service = discovery.build('storage', 'v1', credentials=self.credentials)


    def __build_gs_path(self, remote_file):
        if isinstance(remote_file, list):
            remote_file = os.path.join(*remote_file)
        if len(remote_file) > 0 and remote_file[0] == "/":
            raise ChirriException("bad path '%s'." % remote_file)
        return os.path.join(self.ldb.sm_gs_folder, remote_file)


    def ask_config(self, config):
            while True:
                config["sm_gs_json_creds_file"] = \
                    os.path.realpath(
                        chirribackup.input.ask("JSON API credentials file", config["sm_gs_json_creds_file"]))
                if not os.path.exists(config["sm_gs_json_creds_file"]):
                    print "ERROR: File '%s' does not exists. Try again."
                    continue
                try:
                    with open(config["sm_gs_json_creds_file"]) as data_file:    
                        creds = json.load(data_file)
                except ValueError, ex:
                    print "ERROR: Cannot parse JSON file '%s'. Try again."
                    continue
                break

            config["sm_gs_bucket"] = chirribackup.input.ask("Bucket name", config["sm_gs_bucket"])
            config["sm_gs_folder"] = chirribackup.input.ask("Root folder path", config["sm_gs_folder"])


    def __upload_iobase(self, remote_file, md5sum, f, retry = 0):
        try:
            media = http.MediaIoBaseUpload(
                            f,
                            mimetype="application/octet-stream",
                            resumable=True)
            request = self.service.objects().insert(
                        bucket = self.ldb.sm_gs_bucket,
                        body = {
                            "name"    : self.__build_gs_path(remote_file),
                            "md5Hash" : md5sum,
                        },
                        media_body = media)

            response = None
            last_progress = 0
            while response is None:
                status, response = request.next_chunk()
                if status:
                    current_progress = int(status.progress() * 100)
                    if last_progress != current_progress:
                        last_progress = int(status.progress() * 100)
                        logger.info("    Uploaded %d%%." % current_progress)
            logger.info("    Upload Complete!")

        except socket.error, ex:
            logger.error("errno = %s" % ex.errno)
            if ex.errno == errno.ECONNRESET \
            or ex.errno ==  errno.ETIMEDOUT:
                raise StorageTemporaryCommunicationException(str(ex))
            else:
                raise StoragePermanentCommunicationException(str(ex))


    def upload_file(self, remote_file, local_file):
        # calculate md5sum of uploaded file
        size = 0
        h = hashlib.md5()
        with open(local_file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                size += len(chunk)
                h.update(chunk)
        md5sum = base64.b64encode(h.digest())
        logger.info("Going to upload %s" % (format_num_bytes(size)))

        # upload file
        with open(local_file, "rb") as f:
            self.__upload_iobase(remote_file, md5sum, f)


    def upload_data(self, remote_file, data):
        # calculate md5sum of uploaded file
        md5sum = base64.b64encode(hashlib.md5(data).digest())
        logger.info("Going to upload %s" % format_num_bytes(len(data)))

        # upload file
        self.__upload_iobase(remote_file, md5sum, StringIO.StringIO(data))


    def get_listing(self, path = ""):
        req = self.service.objects().list(
                    bucket = self.ldb.sm_gs_bucket,
                    fields = "nextPageToken,items(name,size)")
        l = []
        while req:
            resp = req.execute()
            for i in resp.get('items', []):
                l.append(
                    {
                        "name" : i["name"][len(self.ldb.sm_gs_folder)+1:],
                        "size" : i["size"],
                    })
            req = self.service.objects().list_next(req, resp)
        return l


    def __download(self, remote_file, f):
        req = self.service.objects().get_media(
                            bucket = self.ldb.sm_gs_bucket,
                            object = self.__build_gs_path(remote_file))
        downloader = http.MediaIoBaseDownload(f, req)

        done = False
        while done is False:
            status, done = downloader.next_chunk()
            logger.info("%s: Download %.2f." % (remote_file, int(status.progress() * 100)))


    def download_file(self, remote_file, local_path):
        with open(local_path, "wb") as f:
            self.__download(remote_file, f)


    def download_data(self, remote_file):
        f = StringIO.StringIO()
        self.__download(remote_file, f)
        return f.getvalue()


    def delete_file(self, remote_file):
        try:
            req = self.service.objects().delete(
                            bucket = self.ldb.sm_gs_bucket,
                            object = self.__build_gs_path(remote_file))
            resp = req.execute()
        except errors.HttpError, ex:
            if ex.resp.status != 404:
                raise ex
            else:
                logger.error("Cannot delete remote file '%s' because it does not exists." \
                                % remote_file)


