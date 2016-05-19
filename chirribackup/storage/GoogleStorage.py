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

from chirribackup.exceptions import ChirriException
from chirribackup.Logger import logger
from googleapiclient import discovery
from googleapiclient import errors
from googleapiclient import http
from oauth2client.service_account import ServiceAccountCredentials
import chirribackup.storage.BaseStorage
import StringIO
import base64
import hashlib
import json
import os


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
                        chirribackup.Input.ask("JSON API credentials file", config["sm_gs_json_creds_file"]))
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

            config["sm_gs_bucket"] = chirribackup.Input.ask("Bucket name", config["sm_gs_bucket"])
            config["sm_gs_folder"] = chirribackup.Input.ask("Root folder path", config["sm_gs_folder"])


    def upload_file(self, remote_file, local_file):
        # calculate md5sum of uploaded file
        size = 0
        h = hashlib.md5()
        with open(local_file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                size += len(chunk)
                h.update(chunk)
        md5sum = base64.b64encode(h.digest())
        logger.debug("Going to upload %d bytes" % size)

        # upload file
        with open(local_file, "rb") as f:
            req = self.service.objects().insert(
                    bucket = self.ldb.sm_gs_bucket,
                    body = {
                        "name"    : self.__build_gs_path(remote_file),
                        "md5Hash" : md5sum,
                    },
                    media_body = http.MediaIoBaseUpload(
                                    f,
                                    "application/octet-stream"))
            resp = req.execute()


    def upload_data(self, remote_file, data):
        # calculate md5sum of uploaded file
        md5sum = base64.b64encode(hashlib.md5(data).digest())
        logger.debug("Going to upload %d bytes" % len(data))

        # upload file
        req = self.service.objects().insert(
                bucket = self.ldb.sm_gs_bucket,
                body = {
                    "name"    : self.__build_gs_path(remote_file),
                    "md5Hash" : md5sum,
                },
                media_body = http.MediaIoBaseUpload(
                                StringIO.StringIO(data),
                                "application/octet-stream"))
        resp = req.execute()


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


