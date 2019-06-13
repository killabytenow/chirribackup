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
import re
import socket
from httplib import HTTPException

from google.oauth2 import service_account
import google.cloud.storage

from chirribackup.Logger import logger
from chirribackup.StringFormat import format_num_bytes
from chirribackup.exceptions import ChirriException, \
                                    StorageTemporaryCommunicationException, \
                                    StoragePermanentCommunicationException
import chirribackup.input
import chirribackup.storage.BaseStorage


class GoogleStorage(chirribackup.storage.BaseStorage.BaseStorage):

    # class attributes
    name = "Google Cloud storage"
    storage_status_keys = {
        "sm_gs_json_creds_file": { "save": 1, "type": "str",  "value": None  },
        "sm_gs_bucket":          { "save": 1, "type": "str",  "value": None  },
        "sm_gs_folder":          { "save": 1, "type": "str",  "value": None  },
        "sm_gs_chunked":         { "save": 1, "type": "bool", "value": False },
    }

    # object attributes
    scopes = None
    credentials = None
    client = None
    bucket = None

    def __init__(self, ldb, config = False):
        super(GoogleStorage, self).__init__(ldb, config)

        if not config:
            # okay .. not in config (ask_config() method)
            # load credentials and authenticate
            self.scopes = ['https://www.googleapis.com/auth/devstorage.read_write']
                         #['https://www.googleapis.com/auth/cloud-platform'])
            logger.debug("Using credentials '%s'" % self.ldb.sm_gs_json_creds_file)
            self.credentials = service_account.Credentials.from_service_account_file(
                                   self.ldb.sm_gs_json_creds_file)
            self.credentials = self.credentials.with_scopes(self.scopes)
            logger.debug("Creating gs client")
            self.client = google.cloud.storage.Client(credentials=self.credentials, project=self.credentials._project_id)
            logger.debug("Setting bucket %s" % self.ldb.sm_gs_bucket)
            self.bucket = self.client.get_bucket(self.ldb.sm_gs_bucket)
            logger.debug("GS storage manager ready")


    def __build_gs_path(self, remote_file):
        if remote_file is None:
            return self.ldb.sm_gs_folder
        if isinstance(remote_file, list):
            remote_file = os.path.join(*remote_file)
        if len(remote_file) > 0 and remote_file[0] == "/":
            raise ChirriException("bad path '%s'." % remote_file)
        if len(self.ldb.sm_gs_folder) == 0:
            return remote_file
        return os.path.join(self.ldb.sm_gs_folder, remote_file)


    def ask_config(self, config):
            while True:
                config["sm_gs_json_creds_file"] = \
                    os.path.realpath(
                        chirribackup.input.ask("JSON API credentials file", config["sm_gs_json_creds_file"]))
                if not os.path.exists(config["sm_gs_json_creds_file"]):
                    logger.error("File '%s' does not exists. Try again." \
                                    % config["sm_gs_json_creds_file"])
                    continue
                try:
                    with open(config["sm_gs_json_creds_file"]) as data_file:    
                        creds = json.load(data_file)
                except ValueError, ex:
                    logger.error("Cannot parse JSON file '%s'. Try again." \
                                    % config["sm_gs_json_creds_file"])
                    continue
                break

            config["sm_gs_bucket"] = chirribackup.input.ask("Bucket name", config["sm_gs_bucket"])
            config["sm_gs_folder"] = chirribackup.input.ask("Root folder path", config["sm_gs_folder"])
            config["sm_gs_chunked"] = chirribackup.input.ask("Chunked uploads and downloads", config["sm_gs_chunked"])


    def __upload_iobase(self, remote_file, md5sum, f, size, retry = 0):
        try:
            if not self.ldb.sm_gs_chunked:
                blob = self.bucket.blob(self.__build_gs_path(remote_file))
                blob.md5_hash = md5sum
                blob.upload_from_file(f, num_retries=retry)

            else:
                #media = http.MediaIoBaseUpload(
                #                f,
                #                mimetype="application/octet-stream",
                #                resumable=True)
                #request = self.service.objects().insert(
                #            bucket = self.ldb.sm_gs_bucket,
                #            body = {
                #                "name"    : self.__build_gs_path(remote_file),
                #                "md5Hash" : md5sum,
                #            },
                #            media_body = media)

                #response = None
                #last_progress = 0
                #while response is None:
                #    status, response = request.next_chunk()
                #    if status:
                #        current_progress = int(status.progress() * 100)
                #        if last_progress != current_progress:
                #            last_progress = int(status.progress() * 100)
                #            logger.info("    Uploaded %d%%." % current_progress)
                #logger.info("    Upload Complete!")
                raise NotImplementedException("__upload_iobase")

            logger.info("    Upload Complete!")

        except socket.error, ex:
            logger.error("errno = %s" % ex.errno)
            if ex.errno == errno.ECONNRESET \
            or ex.errno ==  errno.ETIMEDOUT:
                raise StorageTemporaryCommunicationException(str(ex))
            else:
                raise StoragePermanentCommunicationException(str(ex))

        #except HTTPException, ex:
        #    logger.error("httplib.HTTPException = %s: %s" \
        #        % (ex.__class__.__name__, ex))
        #    raise StorageTemporaryCommunicationException(str(ex))

        #except errors.HttpError, ex:
        #    logger.error("googleapiclient.errors.HttpError = %s" % str(ex))
        #    if re.compile("^<HttpError 5[0-9][0-9] .*$").match(str(ex)) is not None:
        #        raise StorageTemporaryCommunicationException(str(ex))
        #    else:
        #        raise StoragePermanentCommunicationException(str(ex))


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
        if size > 0:
            with open(local_file, "rb") as f:
                self.__upload_iobase(remote_file, md5sum, f, size)
        else:
            logger.info("File of 0 bytes cannot be uploaded to GCS")


    def upload_data(self, remote_file, data):
        # calculate md5sum of uploaded file
        md5sum = base64.b64encode(hashlib.md5(data).digest())
        logger.info("Going to upload %s" % format_num_bytes(len(data)))

        # upload file
        if len(data) > 0:
            self.__upload_iobase(remote_file, md5sum, StringIO.StringIO(data), len(data))
        else:
            logger.info("File of 0 bytes cannot be uploaded to GCS")


    def __get_listing(self, path = ""):
        if path != "":
            path = path + "/"
        logger.debug("Listing bucket '%s' with prefix '%s'." \
                        % (self.ldb.sm_gs_bucket, self.__build_gs_path(path)))
        blobs = self.bucket.list_blobs(prefix=self.__build_gs_path(path))
        l = []
        for blob in blobs:
            if blob.name != self.__build_gs_path(path):
                l.append(
                    {
                        "name" : blob.name[len(self.__build_gs_path(path)):],
                        "size" : blob.size,
                    })
        return l


    def get_listing(self):
        return self.__get_listing()


    def get_listing_chunks(self):
        return self.__get_listing("chunks")


    def get_listing_snapshots(self):
        return self.__get_listing("snapshots")


    def __download(self, remote_file, f):
        """Downloads a blob from the bucket."""
        blob = self.bucket.blob(self.__build_gs_path(remote_file))

        if not self.ldb.sm_gs_chunked:
            blob.download_to_file(f)

        else:
            #done = False
            #while done is False:
            #    status, done = downloader.next_chunk()
            #    logger.info("%s: Download %.2f." % (remote_file, int(status.progress() * 100)))
            raise NotImplementedException("__upload_iobase")


    def download_file(self, remote_file, local_path):
        with open(local_path, "wb") as f:
            self.__download(remote_file, f)


    def download_data(self, remote_file):
        f = StringIO.StringIO()
        self.__download(remote_file, f)
        return f.getvalue()


    def delete_file(self, remote_file):
        blob = self.bucket.blob(self.__build_gs_path(remote_file))
        blob.delete()


