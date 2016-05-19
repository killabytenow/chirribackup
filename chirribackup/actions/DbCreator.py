#!/usr/bin/env python
# -*- coding: UTF-8 -*-
###############################################################################
# chirribackup/actions/DbCreator.py
#
#   Abstract class with a method for configuring a new database. This methods
#   makes a serie of questions, creates a void database and populates it with
#   the data given by the user.
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
from chirribackup.Config import CONFIG
from chirribackup.Logger import logger
import chirribackup.actions.BaseAction
import chirribackup.LocalDatabase
import chirribackup.Input
import chirribackup.exclude
import os
import sys

from chirribackup.storage import BaseStorage


class DbCreator(chirribackup.actions.BaseAction.BaseAction):

    def get_config(self, config):
        if config is None:
            config = {
                "storage_type" : "local",
                "compression"  : "lzma",
            }

        # ask basic things
        print "Basic configuration"
        print "==================="
        print ""
        config["storage_type"] = chirribackup.Input.ask(
                                    "storage type (local, gs)",
                                    config["storage_type"],
                                    "^(local|gs|Local|GoogleStorage)$")
        if config["storage_type"] == "local":
            config["storage_type"] = "Local"
        elif config["storage_type"] == "gs":
            config["storage_type"] = "GoogleStorage"

        config["compression"] = chirribackup.Input.ask(
                                    "storage compression (none, lzma)",
                                    config["compression"],
                                    "^(none|lzma)$")
        if config["compression"] == "none":
            config["compression"] = None

        # Instantiate a config storage manager
        sm = BaseStorage.GetStorageManager(
                config["storage_type"],
                self.ldb,
                config=True)

        # copy default config of storage manager
        for sk,v in sm.storage_status_keys.items():
            if sk in config:
                raise ChirriException("storage key '%s' already exists in basic status_keys." % sk)
            config[sk] = str(v["value"]) if v["value"] is not None else None

        # configure storage module
        sm_title = "Backend '%s' configuration" % sm.name
        print ""
        print "%s" % sm_title
        print "=" * len(sm_title)
        print ""

        sm.ask_config(config)

        # print recollected data and ask for confirmation
        print ""
        print "Confirm"
        print "======="
        print ""
        print "Confirm following data:"
        for k,v in config.items():
            print "  %-15s = %s" % (k, v)
        print ""
        confirm = chirribackup.Input.ask("Continue (yes, no)", "y", "^(y(es)?|n(o)?)$")
        if confirm != "y":
            print "Aborting"
            return None

        return config;


    def create_db(self, config, excludes):
        if not chirribackup.LocalDatabase.check_db_exists(CONFIG.path):
            # build database
            logger.info("Going to initialize database")
            if not os.path.exists(CONFIG.path):
                logger.info("Creating directory '%s'." % CONFIG.path)
                os.makedirs(CONFIG.path)
            self.ldb = chirribackup.LocalDatabase.LocalDatabase(
                            CONFIG.path,
                            init = True,
                            storage_type = config["storage_type"])
            for k,v in config.items():
                setattr(self.ldb, k, v)
            self.ldb.connection.commit()
            logger.info("Database created succesfully.")
        else:
            logger.error("Database already exists.")

        if excludes is not None:
            for x in excludes:
                chirribackup.exclude.Exclude(self.ldb).new(
                        exclude     = x["exclude"],
                        expr_type   = x["expr_type"],
                        ignore_case = x["ignore_case"],
                        disabled    = x["disabled"])


