#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/LocalDatabase.py
#
#   Mantains a local sqlite3 database on the local computer
#   This database is never uploaded, but it can be reconstructed partially
#   using contents found in a remote storage.
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

from chirribackup.Logger import logger
import chirribackup.storage.BaseStorage
import chirribackup.snapshot
import json
import os
import time
import re
import sqlite3

from chirribackup.exceptions import ChirriException, ConfigNotFoundException

DB_VERSION = 2

class LocalDatabase(object):

    __initialized__ = None
    db_path    = None
    db_file    = None
    chunks_dir = None
    connection = None


    def __create_tables(self, storage_type):
        c = self.connection.cursor()

        # basic configuration keys
        status_keys = {
            # db_version
            #   Database version.
            "db_version" :       { "save": 0, "type": "int", "value": DB_VERSION },
            # status
            #   Database status. One of following values:
            #       0  downloading file list
            #       1  downloading snapshots and info
            #       2  select snapshot to restore
            #       3  restoring snapshot
            #     100  normal operations
            "status" :           { "save": 0, "type": "int", "value": 100 },
            # last_snapshot_id
            #   Well, it does not contain really the latest, it actually
            #   contains the biggest snapshot_id assigned.
            "last_snapshot_id" : { "save": 0, "type": "int", "value": 0 },
            # last_exclude_id
            #   It contains the latest exclude id assigned.
            "last_exclude_id"  : { "save": 0, "type": "int", "value": 0 },
            # last_config_id
            #   It contains the latest config id assigned.
            "last_config_id"   : { "save": 0, "type": "int", "value": 0 },
            # rebuild_snapshot
            #   When running 'db rebuild', this attribute contains the target
            #   snapshot that must be restored.
            "rebuild_snapshot" : { "save": 0, "type": "int", "value": None },
            # storage_type
            #   storage backend used for backups. Take a look at
            #   chirribackup/storage/*.py
            "storage_type" :     { "save": 1, "type": "str", "value": None },
            # compression
            #   storage compression
            "compression" :      { "save": 1, "type": "str", "value": None },
        }

        # Create temporary sm for adding specific configuration keys
        sm = chirribackup.storage.BaseStorage.GetStorageManager(
                storage_type,
                ldb=self,
                config=True)
        for sk,v in sm.storage_status_keys.items():
            if sk in status_keys:
                raise ChirriException("storage key '%s' already exists in basic status_keys." % sk)
            status_keys[sk] = v

        # Create table
        c.execute('''
                CREATE TABLE IF NOT EXISTS status (
                    key             TEXT PRIMARY KEY,
                    save            INTEGER NOT NULL,
                    type            VARCHAR(8) NOT NULL CHECK (type = "int" OR type = "str" OR type = "bool"),
                    value           TEXT
                )''')
        for k,v in status_keys.items():
            self.config_attrib_new(k, v["save"], v["type"], v["value"])

        # TABLE: file_data (hash, size)
        #   hash
        #       Content hash
        #   size
        #       Data size
        #   csize
        #       Compressed size
        #   first_seen_as
        #       First time we see that file it was associated to the path
        #       contained in this field.
        #       NOTE: This field is not used for anything useful, only for
        #       recovering in case of a catastrofic event where only some files
        #       can be recovered.
        #   status
        #        0 - chunk waiting for compression & upload
        #        1 - compressed
        #        2 - uploaded
        #   refcount
        #       Snapshots referencing to this data.
        #   deleted
        #     Deletion scheduled
        #   compression
        #     Compression algorithm used (NULL, lzma, ...)
        c.execute('''
                CREATE TABLE IF NOT EXISTS file_data (
                    hash            TEXT,
                    size            INTEGER,
                    csize           INTEGER,
                    first_seen_as   TEXT,
                    status          INTEGER NOT NULL DEFAULT 0,
                    refcount        INTEGER,
                    compression     VARCHAR(8),
                    PRIMARY KEY (hash, size)
                )''')

        # TABLE: file_ref (snapshot, path)
        #   snapshot
        #       Snapshot id (view table "snapshots")
        #   path, perm, uid, gid, mtime
        #       File metadata
        #   hash, size
        #       Associated content (view table "file_data")
        #   status
        #       Work done on this entry:
        #         NULL - Copied from previous snapshot
        #         0    - discovered/checked for this snapshot
        #                attr are updated in this part
        #                please note that hash may be set NULL on this
        #                step for requesting file content rehash
        #         1    - content checked/updated
        #                'hash' field is updated in this step
        #                entries to "file_data" table are inserted here
        #         -1   - error.. cannot backup
        c.execute('''
                CREATE TABLE IF NOT EXISTS file_ref (
                    snapshot        INTEGER,
                    path            TEXT NOT NULL,
                    hash            TEXT,
                    size            INTEGER,
                    perm            INTEGER,
                    uid             INTEGER,
                    gid             INTEGER,
                    mtime           INTEGER,
                    status          INTEGER,
                    PRIMARY KEY (snapshot, path)
                )''')

        # TABLE: snapshots
        #   snapshot
        #       Snapshot id
        #   status
        #       Work done on this entry:
        #        -1   Being rebuilt (discovered in remote repo)
        #         0 - Created, not job done
        #         1 - discovered all files
        #         2 - removed lost files
        #         3 - file content checked
        #         4 - snapshot prepared for upload
        #         5 - uploaded
        #   compression
        #     Compression algorithm used (NULL, lzma, ...)
        #   delete
        #     Deletion scheduled
        c.execute(
            """
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot        INTEGER PRIMARY KEY,
                    status          INTEGER NOT NULL,
                    started_tstamp  INTEGER,
                    finished_tstamp INTEGER,
                    signed_tstamp   INTEGER,
                    compression     VARCHAR(8),
                    deleted         INTEGER NOT NULL DEFAULT 0
                )
            """)

        # TABLE: excludes
        #   exclude
        #       path, wildcard or regex
        #   expr_type
        #       0 literal, 1 wildcard, 2 regex
        #   disabled
        #       0 no, >0 yes
        c.execute(
            """
                CREATE TABLE IF NOT EXISTS excludes (
                    exclude_id  INTEGER PRIMARY KEY,
                    exclude     TEXT NOT NULL,
                    expr_type   INTEGER NOT NULL CHECK (expr_type >= 0 AND expr_type <= 2),
                    ignore_case INTEGER NOT NULL DEFAULT 0,
                    disabled    INTEGER NOT NULL DEFAULT 0
                )
            """)

        # TABLE: config_backups
        #   cb_id
        #       config backup id
        #   status
        #         0 - Created, not uploaded
        #         1 - uploaded
        #   deleted
        #     Deletion scheduled
        c.execute(
            """
                CREATE TABLE IF NOT EXISTS config_backups (
                    config_id   INTEGER PRIMARY KEY,
                    config      TEXT NOT NULL,
                    status      INTEGER NOT NULL CHECK (status = 0 OR status = 1),
                    tstamp      INTEGER NOT NULL,
                    deleted     INTEGER NOT NULL DEFAULT 0
                )
            """)


    def __init__(self, path, init = False, storage_type = None, db_version_check = True):
        super(LocalDatabase, self).__setattr__('db_path', path)
        self.db_file = os.path.join(path, "__chirri__.db")
        self.chunks_dir = os.path.join(path, "__chunks__")
        #self.initialized = init
        self.__initialized__ = True

        # check if db file exists
        if os.path.isfile(self.db_file):
            if init:
                raise ChirriException("Local database '%s' already exists." % self.db_file)
            logger.debug("Connecting to database '%s'." % self.db_file)
        else:
            if not init:
                raise ChirriException("A local database in directory '%s' does not exist." % self.db_path)
            logger.info("Creating database '%s'." % self.db_file)

        # connect to database
        self.connection = sqlite3.connect(self.db_file)
        self.connection.row_factory = sqlite3.Row
        self.connection.text_factory = str

        if init:
            self.__create_tables(storage_type)

        if self.db_version != DB_VERSION:
            if db_version_check:
                raise ChirriException(
                        "Old database (version %d), expected version %s -- run 'db check'" \
                        % (self.db_version, DB_VERSION))
            logger.warning("DETECTED OLD DATABASE VERSION %d, EXPECTED VERSION %d" \
                    % (self.db_version, DB_VERSION))

        # chunks directory should always exist...
        if not os.path.exists(self.chunks_dir):
            os.mkdir(self.chunks_dir, 0700)


    def snapshot_list(self):
        slist = []
        for row in self.connection.execute("SELECT snapshot FROM snapshots"):
            slist.append(chirribackup.snapshot.Snapshot(self).load(row["snapshot"]))
        return slist


    def counters(self):
        counters = { }

        # chunk count
        for counter,query in {
                    # chunks count
                    "chunks":
                        "SELECT COUNT(*) FROM file_data",
                    "chunks_not_uploaded":
                        "SELECT COUNT(*) FROM file_data WHERE status < 2",
                    "chunks_uploaded":
                        "SELECT COUNT(*) FROM file_data WHERE status = 2",
                    "chunks_not_referenced":
                        "SELECT COUNT(*) FROM file_data WHERE refcount = 0",

                    # chunks' volume count
                    "chunks_bytes":
                        "SELECT SUM(size) FROM file_data",
                    "chunks_bytes_not_referenced":
                        "SELECT SUM(size) FROM file_data WHERE refcount = 0",
                    "chunks_bytes_uploaded":
                        "SELECT SUM(size) FROM file_data WHERE status = 2",
                    "chunks_bytes_pending_upload":
                        "SELECT SUM(size) FROM file_data WHERE status < 2",

                    # chunks' compressed volume count
                    "chunks_compressed_bytes":
                        "SELECT SUM(csize) FROM file_data",
                    "chunks_compressed_bytes_not_referenced":
                        "SELECT SUM(csize) FROM file_data WHERE refcount = 0",
                    "chunks_compressed_bytes_uploaded":
                        "SELECT SUM(csize) FROM file_data WHERE status = 2",
                    "chunks_uncompressed_bytes_pending_upload":
                        "SELECT SUM(csize) FROM file_data WHERE status = 0",
                    "chunks_compressed_bytes_pending_upload":
                        "SELECT SUM(csize) FROM file_data WHERE status = 1",

                    # count snapshots
                    "snapshots":
                        "SELECT COUNT(*) FROM snapshots",

                    # count excludes
                    "excludes":
                        "SELECT COUNT(*) FROM excludes",
                }.iteritems():
            counters[counter] = self.connection.execute(query).fetchone()[0]
            if counters[counter] is None:
                counters[counter] = 0

        counters["file_refs"] = { }
        for fr in self.connection.execute("""
                                SELECT snapshot, COUNT(*) as nfr
                                FROM file_ref
                                GROUP BY snapshot
                            """):
            counters["file_refs"][fr["snapshot"]] = fr["nfr"]

        # compression by algorithms
        counters["compression"] = { }
        for ac in self.connection.execute(
                        """
                            SELECT compression,
                                    SUM(csize) AS csize,
                                    SUM(size)  AS size
                            FROM file_data
                            WHERE status == 2
                            GROUP BY compression
                        """):
            counters["compression"][ac["compression"]] = {
                    "csize": ac["csize"],
                    "size":  ac["size"],
                    "ratio": 1.0 if ac["size"] == 0 \
                                else (float(ac["csize"]) \
                                        / float(ac["size"])),
                }

        # some calculus
        counters["compression_ratio"] = \
            1.0 if counters["chunks_bytes"] == 0 \
            else (float(counters["chunks_compressed_bytes"]) \
                    / float(counters["chunks_bytes"]))

        counters["chunks_bytes_pending_upload"] = \
                    counters["chunks_uncompressed_bytes_pending_upload"] \
                    + counters["chunks_compressed_bytes_pending_upload"]

        return counters


    def get_storage_manager(self):
        return chirribackup.storage.BaseStorage.GetStorageManager(
                        self.storage_type,
                        ldb=self,
                        config=False)


    def is_db_file(self, rel_path):
        if rel_path == "__chunks__" \
        or rel_path == "__chirri__.db" \
        or rel_path == "__chirri__.db-journal":
            return True

        return False

    def config_attrib_list(self):
        status = {}
        for kv in self.connection.execute("SELECT * FROM status"):
            status[kv["key"]] = {
                "save":  kv["save"],
                "type":  kv["type"],
                "value": kv["value"],
            }
        status["db_path"]    = { "save": 0, "type": "str", "value": self.db_path }
        status["db_file"]    = { "save": 0, "type": "str", "value": self.db_file }
        status["chunks_dir"] = { "save": 0, "type": "str", "value": self.chunks_dir }
        return status


    def config_attrib_check_and_fix(self, entry_type, key, value):
        if entry_type == "int":
            try:
                if value is not None:
                    int(value)
            except ValueError, ex:
                raise AttributeError("attribute %s requires None or int value (value = %s)." % (key, value))

            value = str(value)

        elif entry_type == "bool":
            if re.compile("^(y(es)?|true)$", re.IGNORECASE).match(str(value)):
                value = "true"
            elif re.compile("^(no?|false)$", re.IGNORECASE).match(str(value)):
                value = "false"
            else:
                raise AttributeError("attribute %s requires true or false value (value = %s)." % (key, value))

        elif entry_type == "str":
            """everything ok"""

        else:
            raise AttributeError("attribute %s has unknown type %s" % (key, entry_type))

        return value

    def config_attrib_new(self, key, save, entry_type, value):
        if self.connection is None:
            raise ChirriException("Database not connected. Cannot write attribute '%s' in %s object" \
                                            % (key, self.__class__.__name__))
        value = self.config_attrib_check_and_fix(entry_type, key, value)

        self.connection.execute(
            """
                INSERT INTO status
                    (key, save, type, value)
                VALUES (:key, :save, :type, :value)
            """, {
                "key"   : key,
                "save"  : save,
                "type"  : entry_type,
                "value" : value,
            });


    def config_attrib_set(self, key, value):
            if self.connection is None:
                raise ChirriException("Database not connected. Cannot write attribute '%s' in %s object" \
                                            % (key, self.__class__.__name__))
            ra = self.connection.execute(
                    "SELECT save, type, value FROM status WHERE key = :key",
                    { "key": key }).fetchone()
            if ra is None:
                raise AttributeError("%s object has no %r attribute" \
                                        % (self.__class__.__name__, key))
            value = self.config_attrib_check_and_fix(ra["type"], key, value)
            c = self.connection.execute(
                    """
                        UPDATE status
                        SET value = :val
                        WHERE key = :key
                    """, {
                        "key": key,
                        "val": value,
                    })
            if c.rowcount <= 0:
                raise AttributeError("%s object has no %r attribute" \
                                        % (self.__class__.__name__, key))


    def config_attrib_get(self, key):
        if self.connection is not None:
            ra = self.connection.execute(
                    "SELECT save, type, value FROM status WHERE key = :key",
                    { "key": key }).fetchone()
            if ra is None:
                raise AttributeError("%s object has no %r attribute" \
                                        % (self.__class__.__name__, key))
        else:
            raise ChirriException("Database not connected. Cannot read attribute '%s' in %s object" \
                                        % (key, self.__class__.__name__))
        if ra["value"] is None:
            return None
        if ra["type"] == "int":
            return int(ra["value"])
        if ra["type"] == "bool":
            if ra["value"] == "true":
                return True;
            if ra["value"] == "false":
                return False;
            raise ChirriException("Bad value '%s' for boolean in status key '%s'." \
                                    % (ra["value"], key))
        if ra["type"] == "str":
            return ra["value"]
        raise ChirriException("Unknown type '%s' in status key '%s'." % (ra["type"], key))


    def config_attrib_delete(self, key):
            c = self.connection.execute(
                    """
                        DELETE FROM status
                        WHERE key = :key
                    """, {
                        "key": key,
                    })
            if c.rowcount <= 0:
                raise AttributeError("%s object has no %r attribute" \
                                        % (self.__class__.__name__, key))


    def __getattr__(self, attr):
        return self.config_attrib_get(attr)


    def __setattr__(self, attr, value):
        if attr in [
                        "__initialized__",
                        "chunks_dir",
                        "db_file",
                        "db_path",
                    ]:
            if self.__initialized__:
                raise AttributeError("Attribute %s in %s object is read ony." \
                                        % (self.__class__.__name__, attr))
            else:
                self.__dict__[attr] = value
        elif attr in [ "connection" ]:
            self.__dict__[attr] = value
        else:
            self.config_attrib_set(attr, value)
        return value


    def config_snapshot(self):
        # get status table (remove not saveable elements)
        status = self.config_attrib_list()
        for k, s in status.items():
            if s["save"] == 0:
                del(status[k])

        # load excludes
        excludes = []
        for x in self.connection.execute("SELECT * FROM excludes"):
            excludes.append({
                "exclude"     : x["exclude"],
                "expr_type"   : x["expr_type"],
                "ignore_case" : x["ignore_case"],
                "disabled"    : x["disabled"],
            })

        # compose config string
        return \
            {
                "status": status,
                "excludes" : excludes,
            }


    def config_get(self, config_id = None):
        r = []

        select = "SELECT * FROM config_backups"
        if config_id is not None:
            select = select + " WHERE config_id = :config_id"
        for c in self.connection.execute(select, { "config_id" : config_id }):
            r.append(
                {
                    "config_id" : c["config_id"],
                    "config"    : LocalDatabase.config_parse(c["config"]),
                    "status"    : c["status"],
                    "tstamp"    : c["tstamp"],
                    "deleted"   : c["deleted"],
                })
        if len(r) == 0 and config_id is not None:
            raise ConfigNotFoundException(
                    "There is not any saved config yet" \
                        if config_id is None else \
                            "Cannot find saved config '%s'." % config_id)
       
        return r if config_id is None else r[0]


    def config_save(self):
        # get config string
        config = json.dumps(self.config_snapshot())

        # get new config id
        config_id = self.last_config_id + 1
        self.last_config_id = config_id

        self.connection.execute(
            """
                INSERT INTO config_backups
                    (config_id, config, status, tstamp, deleted)
                VALUES (:config_id, :config, 0, :tstamp, 0)
            """, {
                "config_id" : config_id,
                "config"    : config,
                "tstamp"    : int(time.time()),
            });


    def config_delete(self, config_id):
        self.connection.execute(
                """
                    UPDATE config_backups
                    SET deleted = 1
                    WHERE config_id = :config_id
                """, {
                    "config_id": config_id,
                })


    def config_destroy(self, config_id):
        self.connection.execute(
                """
                    DELETE FROM config_backups
                    WHERE config_id = :config_id
                """, {
                    "config_id": config_id,
                })

    @classmethod
    def config_parse(cls, config):
        return json.loads(config)


def check_db_exists(path):
    return os.path.isfile(os.path.join(path, "__chirri__.db"))


