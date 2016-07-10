#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/snapshot.py
#
#   Snapshot manager
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

import fnmatch
import json
import os
import re
import shutil
import stat
import time
import sys

import chirribackup.chunk
import chirribackup.crypto
from chirribackup.Logger import logger
from chirribackup.exceptions import ChirriException


class Snapshot(object):

    ldb             = None
    snapshot_id     = None
    status          = None
    deleted         = None
    started_tstamp  = None
    finished_tstamp = None
    signed_tstamp   = None
    compression     = None

    def __init__(self, ldb):
        self.ldb = ldb
        self.snapshot_id = None


    def new(self, base_snapshot_id = None, snapshot_id = None):
        # get 'snapshot_id' and increment 'last_snapshot_id'
        if snapshot_id is None:
            self.snapshot_id = self.ldb.last_snapshot_id + 1
            self.ldb.last_snapshot_id = self.snapshot_id
        else:
            snapshot_id = int(snapshot_id)
            if self.ldb.connection.execute(
                    "SELECT COUNT(*) FROM snapshots WHERE snapshot = :id",
                    { "id" : snapshot_id }).fetchone()[0] > 0:
                raise ChirriException("Snapshot with id %d already exists." % snapshot_id)
            last_snapshot_id = self.ldb.connection.execute(
                        "SELECT MAX(snapshot) FROM snapshots").fetchone()[0]
            if last_snapshot_id is not None:
                last_snapshot_id = int(last_snapshot_id)
            if last_snapshot_id is None or last_snapshot_id < snapshot_id:
                last_snapshot_id = snapshot_id
            self.ldb.last_snapshot_id = last_snapshot_id
            self.snapshot_id = snapshot_id

        # set the rest of basic properties
        self.status          = 0
        self.deleted         = None
        self.started_tstamp  = None
        self.finished_tstamp = None
        self.signed_tstamp   = None
        self.compression     = None

        # create snapshot
        self.ldb.connection.execute("INSERT INTO snapshots (snapshot, status) VALUES ( :id, 0 )",
                    { "id": self.snapshot_id })

        # copy base snapshot
        if base_snapshot_id is not None:
            logger.info("Copying data from base snapshot %d" % base_snapshot_id)
            if self.ldb.connection.execute("SELECT * FROM snapshots WHERE snapshot = :id",
                        { "id": base_snapshot_id }).fetchone() is None:
                raise ChirriException("Snapshot '%d' does not exists." % base_snapshot_id)

            for fr in self.ldb.connection.execute("SELECT * FROM file_ref WHERE snapshot = :id",
                                    { "id": base_snapshot_id }):
                logger.debug("[CHK] %s" % fr["path"])
                self.file_ref_save(fr["path"], fr["hash"], fr["size"], fr["perm"],
                                   fr["uid"], fr["gid"], fr["mtime"], None)
        return self


    def load(self, snapshot_id):
        row = self.ldb.connection.execute(
                    "SELECT * FROM snapshots WHERE snapshot = :snapshot_id",
                    { "snapshot_id" : snapshot_id }).fetchone()
        if row is None:
            raise ChirriException("Snapshot '%d' does not exists." % snapshot_id)

        self.snapshot_id     = row["snapshot"]
        self.status          = row["status"]
        self.deleted         = row["deleted"]
        self.started_tstamp  = row["started_tstamp"]
        self.finished_tstamp = row["finished_tstamp"]
        self.signed_tstamp   = row["signed_tstamp"]
        self.compression     = row["compression"]
        return self


    def refs(self):
        srlist = []
        for row in self.ldb.connection.execute(
                        """
                            SELECT file_ref.*,
                                   file_data.csize,
                                   file_data.compression
                            FROM file_ref LEFT JOIN file_data
                                ON file_ref.hash = file_data.hash
                            WHERE file_ref.snapshot = :snapshot
                        """, {
                            "snapshot" : self.snapshot_id,
                        }):
            srlist.append({
                    "path"        : row["path"],
                    "hash"        : row["hash"],
                    "size"        : row["size"],
                    "compression" : row["compression"],
                    "csize"       : row["csize"],
                    "perm"        : row["perm"],
                    "uid"         : row["uid"],
                    "gid"         : row["gid"],
                    "mtime"       : row["mtime"],
                    "status"      : row["status"],
                })
        return srlist


    def file_ref_type(self, hash_ref):
        if hash_ref is None:
            return "regfile"
        if hash_ref == "dir":
            return "dir"
        if hash_ref.startswith("symlink:"):
            return "symlink"
        if chirribackup.crypto.ChirriHasher.hash_check(hash_ref):
            return "regfile"
        raise ChirriException("Unknown file_ref type '%s'." % hash_ref)


    def file_ref_symlink(self, hash_ref):
        if self.file_ref_type(hash_ref) != "symlink":
            raise ChirriException("file_ref hash '%s' is not a symlink." % self.file_ref_format(hash_ref))

        return hash_ref[len("symlink:"):]


    def file_ref_format(self, hash_ref):
        htype = self.file_ref_type(hash_ref)

        if htype == "regfile":
            if hash_ref is None:
                return "file_not_hashed"
            else:
                return chirribackup.crypto.ChirriHasher.hash_format(hash_ref)
        elif htype == "dir":
            return "dir"
        elif htype == "symlink":
            return hash_ref
        raise ChirriException("Unknown file_ref type '%s'." % hash_ref)


    def file_ref_save(self, path, hash_or_type, size, perm, uid, gid, mtime, status):
        c = self.ldb.connection.cursor()

        # status assert
        if status is not None:
            if (status < -1 or status > 1):
                raise ChirriException("Invalid status %d for path '%s'." % (status, path))

            if self.file_ref_type(hash_or_type) != "regfile" \
            and status == 0:
                raise ChirriException("Invalid status %d for path '%s' of type %s." \
                                        % (status, path, self.file_ref_type(hash_or_type)))

        # fetch file_ref old info
        c.execute(
            """
                SELECT *
                FROM file_ref
                WHERE snapshot = :snapshot
                    AND path = :path
            """, {
                "snapshot" : self.snapshot_id,
                "path"     : path,
            })
        f = c.fetchone()

        if f is None:
            # this is a new file ... store it in database
            logger.debug("[NEW] %s" % path)
            c.execute(
                """
                INSERT INTO file_ref
                    (snapshot, path, hash, size, perm, uid, gid, mtime)
                VALUES
                    (:snapshot, :path, :hash_or_type, :size, :perm, :uid, :gid, :mtime)
                """, {
                    "snapshot"     : self.snapshot_id,
                    "path"         : path,
                    "hash_or_type" : hash_or_type,
                    "size"         : size,
                    "perm"         : perm,
                    "uid"          : uid,
                    "gid"          : gid,
                    "mtime"        : mtime,
                })
        else:
            touched = False

            # check that file type is the same (if not, then reset hash to new value)
            if self.file_ref_type(hash_or_type) != self.file_ref_type(f["hash"]):
                touched = True

            # if symlink changed...
            if self.file_ref_type(hash_or_type) == "symlink" and hash_or_type != f["hash"]:
                touched = True

            # if regfile and hash declared, then force update hash
            if self.file_ref_type(hash_or_type) == "regfile" \
            and hash_or_type is not None \
            and hash_or_type != f["hash"]:
                touched = True

            # if a permission attribute has changed, then
            #   - update it with v[1],
            #   - if v[0] == true:
            #         then ask for rehashing
            #         else do not ask for rehashing
            for k,v in ({
                            "perm"  : [ False, perm  ],
                            "uid"   : [ False, uid   ],
                            "gid"   : [ False, gid   ],
                            "size"  : [ True,  size  ],
                            "mtime" : [ True,  mtime ],
                        }).items():
                if(f[k] != v[1]):
                    touched = touched or v[0]
                    c.execute(
                        """
                            UPDATE file_ref SET %s = :val
                            WHERE snapshot = :snapshot AND path = :path
                        """ % k, {
                            "snapshot" : self.snapshot_id,
                            "path"     : path,
                            "val"      : v[1]
                        })
                    logger.debug("[UPD] %s (new(%s): %s; old: %s; touched = %s)" \
                                % (path, k, v[1], f[k], touched))

            # if needs update, then update hash
            if touched:
                c.execute(
                    """
                        UPDATE file_ref SET hash = :hash
                        WHERE snapshot = :snapshot AND path = :path
                    """, {
                        "snapshot" : self.snapshot_id,
                        "path"     : path,
                        "hash"     : hash_or_type,
                    })

        # set file ref status
        c.execute(
            """
                UPDATE file_ref SET status = :status
                WHERE snapshot = :snapshot AND path = :path
            """, {
                "status"   : status,
                "snapshot" : self.snapshot_id,
                "path"     : path,
            })

        # update refcount
        if hash_or_type is not None and self.file_ref_type(hash_or_type) == "regfile":
            chunk = chirribackup.chunk.Chunk(self.ldb, hash_or_type)
            chunk.refcount_inc()


    def run_discover_files(self, target_path = "."):
        # cache base path for local operationa -- this is always the 'db_path', never changes
        base = os.path.realpath(self.ldb.db_path)

        ########################################
        # PATH CALCULATIONS
        ########################################

        # get absolute path for target file
        # NOTE:
        #   We do not use realpath() here because we want to know where the
        #   target file resides, not where it is pointing.
        #   Please note that we only iterate on real directories, and we never
        #   will follow a symlink in the next recursive calls.
        path = os.path.abspath(os.path.join(base, target_path))

        # check that target path is inside 'base'
        if not path.startswith(os.path.join(base, "")) and path != base:
            logger.warning("Path '%s' outside of base path '%s' -- ignored" % (target_path, base))
            return

        # remove the 'base' path from the target_path, so
        # '/home/user/backup_dir/dir/file' is converted to 'dir/file' assuming
        # that directory '/home/user/backup_dir' is the base component.
        target_path = path[len(os.path.join(base, "")):]

        # oookay, now we have:
        #   - base        = realpath of the base dir (/home/user/backup_dir)
        #   - path        = abspath of target file (/home/user/backup_dir/dir/file)
        #   - target_path = target file relative to 'base' (dir/file)

        ########################################
        # REGISTER PATH/FILE_REF
        ########################################

        # check if file is excluded
        if self.ldb.is_db_file(target_path):
            return

        # get file stats
        os.stat_float_times(False)
        statinfo = os.lstat(os.path.join(base, path))

        # decide type
        hash_or_type = "bad"
        if stat.S_ISDIR(statinfo.st_mode):
            hash_or_type = "dir"
        elif stat.S_ISLNK(statinfo.st_mode):
            hash_or_type = "symlink:%s" % os.readlink(os.path.join(base, path))
        elif stat.S_ISREG(statinfo.st_mode):
            hash_or_type = None

        if hash_or_type == "bad":
            raise ChirriException("Unknown mode %o for %s" % (stat.S_IFMT(statinfo.st_mode), path))

        if base != path:
            self.file_ref_save(
                    target_path,
                    hash_or_type,
                    statinfo.st_size if stat.S_ISREG(statinfo.st_mode) else 0,
                    stat.S_IMODE(statinfo.st_mode) if not stat.S_ISLNK(statinfo.st_mode) else 0,
                    statinfo.st_uid                if not stat.S_ISLNK(statinfo.st_mode) else 0,
                    statinfo.st_gid                if not stat.S_ISLNK(statinfo.st_mode) else 0,
                    statinfo.st_mtime              if not stat.S_ISLNK(statinfo.st_mode) else 0,
                    0 if stat.S_ISREG(statinfo.st_mode) else 1)

        ########################################
        # IF PATH IS DIR, TRAVERSE IT
        ########################################

        # process file depending on its type
        if hash_or_type == "dir":
            for f in os.listdir(path):
                self.run_discover_files(os.path.join(target_path, f))


    def run_find_lost_and_excluded(self):
        base = os.path.realpath(self.ldb.db_path)

        # load exclude list
        xl = []
        for x in self.ldb.connection.execute("SELECT * FROM excludes"):
            if x["disabled"] == 0:
                exclude = x["exclude"]
                if x["expr_type"] > 0:
                    if x["expr_type"] == 1:
                        exclude = fnmatch.translate(exclude)
                        if exclude.startswith("\\/"):
                            exclude = "^" + exclude[2:]
                        else:
                            exclude = "(\\A|\\/)" + exclude
                    if x["ignore_case"] != 0:
                        exclude = re.compile(exclude, re.IGNORECASE)
                    else:
                        exclude = re.compile(exclude)
                xl.append(exclude)

        # delete excluded or lost files
        for fr in self.ldb.connection.execute(
                    """
                        SELECT *
                        FROM file_ref
                        WHERE snapshot = :snapshot
                    """,
                    { "snapshot" : self.snapshot_id }):

            delete = False

            # delete excluded files
            for x in xl:
                if isinstance(x, basestring):
                    delete = (fr["path"] == x)
                else:
                    delete = x.search(fr["path"]) is not None
                if delete:
                    logger.info("[EXC] %s" % fr["path"])
                    break

            # delete lost files
            if not delete and not os.path.exists(os.path.join(base, fr["path"])):
                logger.warning("[DEL] %s" % fr["path"])
                delete = True

            # execute deletion (if requested)
            if delete:
                self.ldb.connection.execute(
                    """
                        DELETE FROM file_ref
                        WHERE snapshot = :snapshot AND path = :path
                    """, {
                        "snapshot" : self.snapshot_id,
                        "path"     : fr["path"]
                    })
                if fr["hash"] is not None \
                and self.file_ref_type(fr["hash"]) == "regfile":
                    chunk = chirribackup.chunk.Chunk(self.ldb, fr["hash"])
                    chunk.refcount_dec()


    def run_hashy_hasher(self):
        """do the hashy hashy"""
        base = os.path.realpath(self.ldb.db_path)

        for fr in self.ldb.connection.execute(
                    """
                        SELECT *
                        FROM file_ref
                        WHERE snapshot = :snapshot
                    """,
                    { "snapshot" : self.snapshot_id }):
            fr_type = self.file_ref_type(fr["hash"])

            if fr_type == "regfile" and fr["hash"] is None:
                # do snapshot and calc hash
                c = chirribackup.chunk.Chunk(self.ldb)
                try:
                    # make a snapshot of file
                    # NOTE: by default because performance we do not ask for
                    #       any compression for the associated chunk...
                    #       compression will be performed during syncing
                    logger.info("snapshot of '%s'" % fr["path"])
                    c.new(fr["path"])

                    # snapshot succesful: register reference and update
                    # chunk ref counter
                    c.refcount_inc()
                except chirribackup, ex:
                    # snapshot failed: tag file_ref as failed
                    logger.warning("%s: Cannot snapshot file: %s" % (fr["path"], ex))
                    c = None
                self.ldb.connection.execute(
                    """
                        UPDATE file_ref
                        SET status = 1, hash = :hash, size = :size
                        WHERE snapshot = :snapshot
                          AND path = :path
                    """, {
                        "status"   : 1      if c is not None else -1,
                        "hash"     : c.hash if c is not None else None,
                        "size"     : c.size if c is not None else None,
                        "snapshot" : self.snapshot_id,
                        "path"     : fr["path"],
                    })


    def set_status(self, status, commit = True):
        if status < -1 or status > 5:
            raise ChirriException("Bad status %d." % status)
        if int(self.ldb.status) >= 100 and status < 0:
            raise ChirriException("Status %d cannot be used when database is not in rebuild state." % status)
        self.ldb.connection.execute("""
                                UPDATE snapshots
                                SET status = :status
                                WHERE snapshot = :snapshot
                            """, {
                                "snapshot": self.snapshot_id,
                                "status": status,
                            })
        self.status = status

        # commit -- a status change is a good commit point
        if commit:
            self.ldb.connection.commit()


    def set_attribute(self, attribute, value):
        if attribute not in [
                                "compression",
                                "deleted",
                                "finished_tstamp",
                                "started_tstamp",
                                "signed_tstamp",
                            ]:
            raise ChirriException("Invalid snapshot attribute '%s'." % attribute)
        self.ldb.connection.execute(
            """
                UPDATE snapshots
                SET %s = :value
                WHERE snapshot = :snapshot
            """ % attribute, {
                        "snapshot": self.snapshot_id,
                        "value": value,
            })
        return setattr(self, attribute, value)


    def delete(self):
        # tag as deleted this snapshot
        self.set_attribute("deleted", 1)


    def run(self):
        if self.status < 0 or self.status > 5:
            raise ChirriException("Bad status '%d'.", self.status)

        while self.status < 4:
            if self.status == 0:
                logger.info("Starting file discovering (pass 0)")
                self.ldb.connection.execute(
                    """
                        UPDATE snapshots
                        SET started_tstamp = :tstamp
                        WHERE snapshot = :snapshot
                    """, {
                                "snapshot": self.snapshot_id,
                                "tstamp": int(time.time()),
                    })
                self.run_discover_files()
                self.set_status(1)
            if self.status == 1:
                logger.info("Removing lost and excluded files (pass 1)")
                self.run_find_lost_and_excluded()
                self.set_status(2)
            if self.status == 2:
                logger.info("Hashing files (pass 2)")
                self.run_hashy_hasher()
                self.set_status(3)
            if self.status == 3:
                self.ldb.connection.execute(
                    """
                        UPDATE snapshots
                        SET finished_tstamp = :tstamp
                        WHERE snapshot = :snapshot
                    """, {
                                "snapshot": self.snapshot_id,
                                "tstamp": int(time.time()),
                    })
                self.set_status(4)
            else:
                raise ChirriException("Manager for status %d not programmed." % self.status)

        if self.status == 4:
            logger.info("Snapshot %d completed -- scheduled for upload" % self.snapshot_id)
        elif self.status == 5:
            logger.info("Snapshot %d already finished and uploaded" % self.snapshot_id)
        else:
            logger.error("Snapshot %d in unknown state %d." % (self.snapshot_id, self.status))


    def __desc_parse_json(self, desc):
        try:
            d = json.loads(desc)
            if "format" not in d["details"]:
                d["format"] = "json"
            if "default" not in d:
                d["default"] = {}
        except ValueError, ex:
            logger.debug("Cannot parse as JSON string: %s" % ex)
            return None
        return d


    def __desc_parse_csv(self, desc):
        d = {
            "details": {},
            "default": {},
            "refs": [],
        }

        desc = desc.splitlines()
        keyval_re = re.compile("^([^:\\s]+)\\s*:\\s*(.+?)\\s*$")
        defkey_re = re.compile("^default\\.(.+)$")

        # read header
        while len(desc) > 0:
            l = desc.pop(0).strip()
            m = keyval_re.match(l)
            if m is not None:
                k = m.group(1)
                v = m.group(2)
                m = defkey_re.match(k)
                if m is not None:
                    d["default"][m.group(1)] = v
                else:
                    d["details"][k] = v
            elif l == "rows:":
                # going to eat rows as cows
                break
            else:
                logger.error("Cannot parse line '%s'." % l)
                return None

        if d["details"]["format"] != "csv":
            logger.error("Unsupported format '%s'." % d["details"]["format"])
            return None

        if len(desc) == 0:
            logger.warning("No refs found.")
            return d

        # read headers
        headers = desc.pop(0).split(";")

        # parse lines
        while len(desc) > 0:
            l = desc.pop(0).split(";")
            r = {}
            for i in range(0, len(headers)):
                if l[i] != "":
                    r[headers[i]] = l[i].decode("string_escape")
            d["refs"].append(r)
        return d

            
    def desc_parse(self, desc):
        # unprotect
        desc = chirribackup.crypto.unprotect_string(desc)

        # try with json decoder
        d = self.__desc_parse_json(desc)

        # try with CSV decoder
        if d is None:
            d = self.__desc_parse_csv(desc)

        # if we cannot decode this throw an exception
        if d is None:
            raise BadSnapshotDescException("Cannot parse snapshot description")
        
        # retrocompatibility fix: during development of version 1,
        # 'uploaded_tstamp' field was renamed to 'signed_tstamp'
        if "uploaded_tstamp" in d["details"]:
            d["details"]["signed_tstamp"] = d["details"]["uploaded_tstamp"]
            del d["details"]["uploaded_tstamp"]

        # check snapshot is in status < 0
        if self.status >= 0:
            raise BadSnapshotStatusException("Snapshot %s is in state %d." \
                                                % (self.snapshot_id, self.status))
        # uncompress file refs
        for r in d["refs"]:
            for f,dv in d["default"].iteritems():
                if f not in r:
                    #logger.warning("adding %s(%s) in %s" % (f,dv,r))
                    r[f] = dv
        return d


    def desc_load(self, desc):
        # parse snapshot data
        d = self.desc_parse(desc)

        # process d structure
        for a in [
                    "started_tstamp",
                    "finished_tstamp",
                    "signed_tstamp",
                 ]:
            self.set_attribute(a, d["details"][a])
        for fr in d["refs"]:
            self.file_ref_save(
                    fr["path"].encode('utf-8'),
                    fr["hash"].encode('utf-8'),
                    int(fr["size"]),
                    int(fr["perm"]),
                    int(fr["uid"]),
                    int(fr["gid"]),
                    int(fr["mtime"]),
                    int(fr["status"]) if "status" in fr else 1)
        self.set_status(5, False)


    def desc_print(self, output_format = "txt"):
        if self.status < 4:
            raise ChirriException("This snapshot cannot be described -- it is incomplete")

        # fetch all refs
        refs = self.refs()

        # search most common values (space optimization)
        mc = {
            "hash":   {},
            "size":   {},
            "perm":   {},
            "uid":    {},
            "gid":    {},
            "mtime":  {},
            "status": {},
        }
        for r in refs:
            for f,vc in mc.iteritems():
                if r[f] not in vc:
                    vc[r[f]] = 1
                else:
                    vc[r[f]] += 1
        for f in mc.keys():
            mv = None
            for v,c in mc[f].iteritems():
                if mv is None or mc[f][mv] < mc[f][v]:
                    mv = v
            if mv is None:
                del mc[f]
            else:
                if mc[f][mv] > 5:
                    mc[f] = mv
                else:
                    logger.warning("Cannot compress '%s' -- only used %d times." % (f, mc[f][mv]))
                    del mc[f]

        # remove most common values from references
        for r in refs:
            for f in mc.iterkeys():
                if r[f] == mc[f]:
                    del r[f]

        d = None
        if output_format == "json":
            d = json.dumps(
                    {
                        "details" : {
                            "snapshot"        : self.snapshot_id,
                            "started_tstamp"  : self.started_tstamp,
                            "finished_tstamp" : self.finished_tstamp,
                            "signed_tstamp"   : self.signed_tstamp,
                        },
                        "default" : mc,
                        "refs" : refs,
                    })

        elif output_format == "txt":
            d = "format:          csv\n"
            d += "snapshot:        %s\n" % self.snapshot_id
            d += "started_tstamp:  %s\n" % self.started_tstamp
            d += "finished_tstamp: %s\n" % self.finished_tstamp
            d += "signed_tstamp:   %s\n" % self.signed_tstamp
            for f,v in mc.iteritems():
                d += "default.%s: %s\n" % (f, v)
            d += "rows:\n"
            d += "hash;size;perm;uid;gid;mtime;status;path\n"
            for ref in refs:
                d += "%s;%s;%s;%s;%s;%s;%s;%s\n" \
                        % (str(ref["hash"]).encode("string_escape").replace(";", "\\x3b") if "hash" in ref else "",
                           str(ref["size"]).encode("string_escape").replace(";", "\\x3b") if "size" in ref else "",
                           str(ref["perm"]).encode("string_escape").replace(";", "\\x3b") if "perm" in ref else "",
                           str(ref["uid"]).encode("string_escape").replace(";", "\\x3b") if "uid" in ref else "",
                           str(ref["gid"]).encode("string_escape").replace(";", "\\x3b") if "gid" in ref else "",
                           str(ref["mtime"]).encode("string_escape").replace(";", "\\x3b") if "mtime" in ref else "",
                           str(ref["status"]).encode("string_escape").replace(";", "\\x3b") if "status" in ref else "",
                           str(ref["path"]).encode("string_escape").replace(";", "\\x3b") if "path" in ref else "")

        else:
            raise ChirriException("Unknown output format '%s'." % output_format)

        return chirribackup.crypto.protect_string(d)


    def destroy(self):
        if not self.deleted:
            raise ChirriException("Cannot destroy a not-deleted snapshot.")

        # fix reference counters to snapshot's related file_ref
        for fr in self.ldb.connection.execute(
                        "SELECT * FROM file_ref WHERE snapshot = :id",
                        { "id" : self.snapshot_id, }):
            # (if hash is None or symlink/dir doesn't matter)
            fr_type = self.file_ref_type(fr["hash"])
            if fr_type == "regfile" and fr["hash"] is not None:
                chunk = chirribackup.chunk.Chunk(self.ldb, fr["hash"])
                chunk.refcount_dec()

        # delete snapshot's related file_ref
        self.ldb.connection.execute(
            "DELETE FROM file_ref WHERE snapshot = :id",
            { "id" : self.snapshot_id })

        # delete this snapshot
        self.ldb.connection.execute(
            "DELETE FROM snapshots WHERE snapshot = :id",
            { "id" : self.snapshot_id })

        # reset this
        self.snapshot_id     = None
        self.status          = None
        self.started_tstamp  = None
        self.finished_tstamp = None
        self.signed_tstamp   = None

        # commit -- such a status change is a good commit point
        self.ldb.connection.commit()


    def get_filename(self):
        f = "snapshot-%d.txt" % self.snapshot_id
        if self.compression is not None:
            f += "." + self.compression
        return f


    def restore(self, sm, target_path, overwrite = False):
        # some checks
        if self.status < 5:
            raise ChirriException("This snapshot cannot be restored -- it is not uploaded yet")

        target_path = os.path.realpath(target_path)
        logger.info("Restoring snapshot %d in target path '%s'." % (self.snapshot_id, target_path))

        if os.path.exists(target_path):
            if not overwrite:
                raise ChirriException("Target path '%s' already exists." % target_path)

            if not os.path.isdir(target_path):
                raise ChirriException("Target path '%s' is not a directory" % target_path)
            else:
                logger.warning("Target path '%s' already exists -- continuing restoration on it" % target_path)
        else:
            logger.info("Target path '%s' does not exist -- creating" % target_path)
            os.makedirs(target_path, 0770)

        # create directories
        for r in self.refs():
            if self.file_ref_type(r["hash"]) == "dir":
                if not os.path.exists(os.path.join(target_path, r["path"])):
                    os.mkdir(os.path.join(target_path, r["path"]))
                else:
                    os.chmod(os.path.join(target_path, r["path"]), 0700)

        # restore symlinks
        for r in self.refs():
            # process only symlinks
            if self.file_ref_type(r["hash"]) != "symlink":
                continue

            # restore symlink
            target_file = os.path.join(target_path, r["path"])
            symlink = self.file_ref_symlink(r["hash"])
            if os.path.exists(target_file):
                if not overwrite:
                    raise ChirriException("Target file '%s' already exists." % target_file)
                os.unlink(target_file)
            logger.debug("  restoring [%s] (-> %s)" % (target_file, symlink))
            os.symlink(symlink, target_file)

        # organize downloads
        dl = {}
        for r in self.refs():
            # only regular files are processed in this loop
            if self.file_ref_type(r["hash"]) != "regfile":
                continue

            # check if target file exists. If it exists check that its hash
            # match with the chunk's hash
            target_file = os.path.join(target_path, r["path"])
            if os.path.exists(target_file):
                hot = chirribackup.crypto.hash_file(target_file)
                if hot["hex"] == r["hash"]:
                    # target file matches... don't add to the download queue
                    logger.info("File '%s' already downloaded." % r["path"])
                    continue
                # okay ... hashes doesn't match... decide if unlink or abort
                if not overwrite:
                    raise ChirriException("Target file '%s' already exists." % target_file)
                os.unlink(target_file)

            # add a new 'hash' group if does not exist, and then add this file
            # reference to the download queue
            if r["hash"] not in dl:
                dl[r["hash"]] = []
            dl[r["hash"]].append(r)

        # restore files and symlinks
        for h, ref_list in dl.items():
            # download needed chunk
            target_chunk = os.path.join(target_path, ".%s.tmp" % h)
            c = chirribackup.chunk.Chunk(self.ldb, h)
            c.download(sm, target_chunk)

            # once downloaded the needed chunk, we use it for restoring the
            # requested file references
            while len(ref_list) > 0:
                # fetch next element
                r = ref_list.pop(0)

                # debug assertion
                if r["hash"] != h:
                    os.unlink(target_chunk)
                    raise ChirriException("hash not match")

                # overwrite check -- if we found an unexpected file here we
                # must abort. It was created between the download queue build
                # loop (dl) and now, so it is maybe an update or something like
                # that.
                target_file = os.path.join(target_path, r["path"])
                if os.path.exists(target_file):
                    os.unlink(target_chunk)
                    raise ChirriException("Unexpected file '%s' has been found." % target_file)

                # restore file ref
                logger.debug("  restoring [%s]" % target_file)
                if len(ref_list) == 0:
                    os.rename(target_chunk, target_file)
                else:
                    shutil.copyfile(target_chunk, target_file)
                os.utime(target_file, (r["mtime"], r["mtime"]))
                os.chmod(target_file, r["perm"])
                os.chown(target_file, r["uid"], r["gid"])

            # finally we remove the target_chunk file if it stills exists (and
            # we warn about this bug)
            if os.path.exists(target_chunk):
                logger.error("Removing forgotten chunk %s??" % target_chunk)
                os.unlink(target_chunk)

        # restore directory properties
        for r in self.refs():
            target_file = os.path.join(target_path, r["path"])
            if self.file_ref_type(r["hash"]) == "dir":
                os.chmod(target_file, r["perm"])
                os.chown(target_file, r["uid"], r["gid"])
                os.utime(target_file, (r["mtime"], r["mtime"]))


